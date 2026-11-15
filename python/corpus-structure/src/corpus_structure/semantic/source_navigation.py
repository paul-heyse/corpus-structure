"""Explicit, invocation-owned public ty navigation over an exact source snapshot."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import tempfile
import threading
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    path: str
    content: str

    @model_validator(mode="after")
    def relative_path(self):
        path = Path(self.path)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or path.suffix not in {".py", ".pyi"}
            or path.as_posix() != self.path
        ):
            raise ValueError("navigation documents require relative Python source/stub paths")
        return self


class NavigationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    documents: tuple[SourceDocument, ...]
    python_version: Literal["3.14"] = "3.14"

    @model_validator(mode="after")
    def unique_paths(self):
        if len({item.path for item in self.documents}) != len(self.documents):
            raise ValueError("duplicate navigation source path")
        return self

    @property
    def identity(self):
        content = self.model_dump(mode="json")
        content["documents"] = sorted(content["documents"], key=lambda item: item["path"])
        return (
            "source-navigation:"
            + sha256(
                json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
        )


class NavigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_id: str
    path: str
    byte_offset: int = Field(ge=0)
    operation: Literal[
        "definition",
        "declaration",
        "implementation",
        "references",
        "signature",
        "call_hierarchy",
        "type_hierarchy",
    ]
    direction: Literal["incoming", "outgoing", "supertypes", "subtypes"] | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    timeout_seconds: float = Field(default=15, gt=0, le=60)

    @model_validator(mode="after")
    def hierarchy_direction(self):
        expected = {
            "call_hierarchy": {"incoming", "outgoing"},
            "type_hierarchy": {"supertypes", "subtypes"},
        }
        if self.operation in expected and self.direction not in expected[self.operation]:
            raise ValueError("hierarchy navigation requires its explicit direction")
        if self.operation not in expected and self.direction is not None:
            raise ValueError("direction applies only to hierarchy navigation")
        return self


class NavigationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    snapshot_id: str
    tool: str
    operation: str
    standing: Literal["complete", "partial", "unavailable"]
    items: tuple[dict, ...] = ()
    reason: str | None = None


def lsp_position(content: str, byte_offset: int) -> dict:
    raw = content.encode()
    if byte_offset > len(raw):
        raise ValueError("source position exceeds captured bytes")
    prefix = raw[:byte_offset].decode("utf-8")
    return {
        "line": prefix.count("\n"),
        "character": len(prefix.rsplit("\n", 1)[-1].encode("utf-16-le")) // 2,
    }


def _byte_position(content: str, position: dict) -> int:
    lines = content.splitlines(keepends=True)
    line, character = position["line"], position["character"]
    if line == len(lines) and character == 0:
        return len(content.encode())
    if line < 0 or line >= len(lines) or character < 0:
        raise ValueError("ty returned a position outside captured source")
    encoded = lines[line].encode("utf-16-le")
    if character * 2 > len(encoded):
        raise ValueError("ty returned a column outside captured source")
    column = encoded[: character * 2].decode("utf-16-le")
    return len("".join(lines[:line]).encode()) + len(column.encode())


class _Session:
    def __init__(self, root: Path, timeout: float):
        environment = {
            key: value
            for key, value in os.environ.items()
            if key not in {"VIRTUAL_ENV", "PYTHONPATH", "UV_PROJECT_ENVIRONMENT"}
        }
        self.process = subprocess.Popen(
            ["ty", "server"],
            cwd=root,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert self.process.stdin is not None and self.process.stdout is not None
        self.input = self.process.stdin
        self.output = self.process.stdout
        self.messages = queue.Queue()
        self.timeout = timeout
        self.serial = 0
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            while True:
                headers = {}
                while line := self.output.readline():
                    if line in {b"\r\n", b"\n"}:
                        break
                    name, value = line.decode().split(":", 1)
                    headers[name.lower()] = value.strip()
                if not headers:
                    raise EOFError("ty closed its protocol stream")
                self.messages.put(json.loads(self.output.read(int(headers["content-length"]))))
        except Exception as error:
            self.messages.put(error)

    def send(self, message):
        raw = json.dumps({"jsonrpc": "2.0", **message}).encode()
        self.input.write(f"Content-Length: {len(raw)}\r\n\r\n".encode() + raw)
        self.input.flush()

    def notify(self, method, params):
        self.send({"method": method, "params": params})

    def request(self, method, params):
        import time

        self.serial += 1
        serial = self.serial
        self.send({"id": serial, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            message = self.messages.get(timeout=max(0.001, deadline - time.monotonic()))
            if isinstance(message, Exception):
                raise message
            if message.get("id") == serial and "method" not in message:
                if "error" in message:
                    raise ValueError("ty refused navigation: " + str(message["error"].get("code")))
                return message.get("result")
            if "id" in message and "method" in message:
                self.send(
                    {
                        "id": message["id"],
                        "error": {"code": -32601, "message": "client request unsupported"},
                    }
                )
            if time.monotonic() >= deadline:
                raise TimeoutError("ty navigation deadline expired")

    def close(self):
        try:
            if self.process.poll() is None:
                self.request("shutdown", None)
                self.notify("exit", None)
                self.process.wait(timeout=2)
        except Exception, KeyboardInterrupt:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        finally:
            self.input.close()
            self.output.close()


def inspect_source_navigation(
    snapshot: NavigationSnapshot, request: NavigationRequest
) -> NavigationResult:
    """Navigation observations never authorize source edits, reuse or execution."""
    if snapshot.identity != request.snapshot_id:
        raise ValueError("navigation request belongs to another captured snapshot")
    documents = {item.path: item.content for item in snapshot.documents}
    if request.path not in documents:
        raise ValueError("navigation document is outside captured snapshot")
    position = lsp_position(documents[request.path], request.byte_offset)
    tool = "ty unavailable"
    session = None
    try:
        tool = subprocess.run(
            ["ty", "--version"], capture_output=True, text=True, timeout=5, check=True
        ).stdout.strip()
        if tool != "ty 0.0.102":
            raise ValueError("navigation requires selected ty 0.0.102")
        with tempfile.TemporaryDirectory(prefix="corpus-source-navigation-") as directory:
            root = Path(directory)
            for name, content in documents.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content.encode())
            (root / "ty.toml").write_text('[environment]\npython-version = "3.14"\n')
            session = _Session(root, request.timeout_seconds)
            try:
                initialized = session.request(
                    "initialize",
                    {
                        "processId": os.getpid(),
                        "rootUri": root.as_uri(),
                        "capabilities": {},
                        "initializationOptions": {
                            "diagnosticMode": "off",
                            "experimental": {"useUv": "off"},
                            "untrustedWorkspace": True,
                        },
                    },
                )
                capability, method = {
                    "definition": ("definitionProvider", "textDocument/definition"),
                    "declaration": ("declarationProvider", "textDocument/declaration"),
                    "implementation": ("implementationProvider", "textDocument/implementation"),
                    "references": ("referencesProvider", "textDocument/references"),
                    "signature": ("signatureHelpProvider", "textDocument/signatureHelp"),
                    "call_hierarchy": (
                        "callHierarchyProvider",
                        "textDocument/prepareCallHierarchy",
                    ),
                    "type_hierarchy": (
                        "typeHierarchyProvider",
                        "textDocument/prepareTypeHierarchy",
                    ),
                }[request.operation]
                if not initialized.get("capabilities", {}).get(capability):
                    raise ValueError("selected ty does not advertise requested navigation")
                session.notify("initialized", {})
                for name, content in documents.items():
                    session.notify(
                        "textDocument/didOpen",
                        {
                            "textDocument": {
                                "uri": (root / name).as_uri(),
                                "languageId": "python",
                                "version": 1,
                                "text": content,
                            }
                        },
                    )
                params = {
                    "textDocument": {"uri": (root / request.path).as_uri()},
                    "position": position,
                }
                if request.operation == "references":
                    params["context"] = {"includeDeclaration": True}
                result = session.request(method, params)
                rows = result if isinstance(result, list) else [] if result is None else [result]
                partial = len(rows) > request.limit
                if request.operation.endswith("_hierarchy"):
                    assert request.direction is not None
                    next_method = {
                        "incoming": "callHierarchy/incomingCalls",
                        "outgoing": "callHierarchy/outgoingCalls",
                        "supertypes": "typeHierarchy/supertypes",
                        "subtypes": "typeHierarchy/subtypes",
                    }[request.direction]
                    edges = []
                    for item in rows[: request.limit]:
                        edges.extend(session.request(next_method, {"item": item}) or [])
                    rows = edges
                    partial = partial or len(rows) > request.limit
                from urllib.parse import unquote, urlparse

                def attributed(value):
                    nonlocal partial
                    if isinstance(value, list):
                        return [attributed(item) for item in value]
                    if not isinstance(value, dict):
                        return value
                    row = {
                        key: attributed(item)
                        for key, item in value.items()
                        if key not in {"uri", "targetUri"}
                    }
                    uri = value.get("targetUri", value.get("uri"))
                    if uri is not None:
                        parsed_uri = urlparse(uri)
                        path = Path(unquote(parsed_uri.path))
                        if (
                            parsed_uri.scheme != "file"
                            or not path.is_relative_to(root)
                            or path.relative_to(root).as_posix() not in documents
                        ):
                            partial = True
                            return {
                                "standing": "unavailable",
                                "reason": "location outside captured snapshot",
                            }
                        name = path.relative_to(root).as_posix()
                        span = row.get(
                            "targetSelectionRange", row.get("selectionRange", row.get("range"))
                        )
                        row.update(
                            path=name, source_digest=sha256(documents[name].encode()).hexdigest()
                        )
                        if span:
                            row["utf8_bytes"] = {
                                key: _byte_position(documents[name], span[key])
                                for key in ("start", "end")
                            }
                    return row

                mapped = [attributed(row) for row in rows[: request.limit]]
                return NavigationResult(
                    snapshot_id=snapshot.identity,
                    tool=tool,
                    operation=request.operation,
                    standing="partial" if partial else "complete",
                    items=tuple(mapped),
                    reason="result limit or external source location" if partial else None,
                )
            finally:
                session.close()
                session = None
    except (
        OSError,
        ValueError,
        EOFError,
        queue.Empty,
        subprocess.SubprocessError,
    ) as error:
        return NavigationResult(
            snapshot_id=snapshot.identity,
            tool=tool,
            operation=request.operation,
            standing="unavailable",
            reason=str(error) or type(error).__name__,
        )


def archived_navigation_snapshot(connection, release_id: str) -> NavigationSnapshot:
    """Authenticate prepared source headers and original input bytes without reanalysis."""
    from sqlalchemy import select

    from .metadata import table
    from .releases import open_release
    from .source_interfaces import read_source_interfaces

    prepared = open_release(connection, release_id)
    facts = read_source_interfaces(prepared)
    if facts is None:
        raise ValueError("archived release has no prepared source interface projection")
    relation = table("sem.input")
    documents = []
    for module in facts.modules:
        for artifact, expected, suffix in (
            (module.captured_artifact, module.source_digest, ".py"),
            (module.captured_artifact + "i", module.stub_digest, ".pyi"),
        ):
            if expected is None:
                continue
            row = connection.execute(
                select(relation.c.content, relation.c.content_digest).where(
                    relation.c.release_id == release_id,
                    relation.c.input_kind == "dependency",
                    relation.c.input_name == artifact,
                )
            ).one()
            content = bytes(row.content)
            if sha256(content).hexdigest() != expected or row.content_digest != expected:
                raise ValueError("archived navigation source differs from prepared identity")
            name = (
                module.module.replace(".", "/")
                + ("/__init__" if module.path.endswith("/__init__.py") else "")
                + suffix
            )
            documents.append(SourceDocument(path=name, content=content.decode("utf-8")))
    return NavigationSnapshot(documents=tuple(documents))
