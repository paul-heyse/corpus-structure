"""Durable private completion custody before a native intent commits.

The acknowledged request keeps its original producer fence and execution evidence.
Reading a draft establishes local custody. Native settlement owns use authority.
"""

from __future__ import annotations

import fcntl
import os
import re
import stat
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from .data_operation_json import json_bytes, wire_json_loads
from .data_operation_wire import validate_wire_schema, wire_contracts

SUPPORTED_OPERATIONS = frozenset({"source.pdf/capture", "segment.sentences/source-native"})


@dataclass(frozen=True)
class CompletionDraft:
    identity: str
    release_id: str
    operation: str
    basis: bytes
    request: bytes

    def native_request(self) -> dict[str, Any]:
        """Return the exact original native intake request under its captured fence."""
        return wire_json_loads(self.request)


def _identity(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("completion draft requires its exact content identity")
    return value


def _sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _read(path: Path, *, max_bytes: int, expected_bytes: int | None = None) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError("completion draft has foreign file custody")
        if info.st_size > max_bytes or (
            expected_bytes is not None and info.st_size != expected_bytes
        ):
            raise ValueError("completion draft differs from its bounded expected extent")
        with os.fdopen(fd, "rb", closefd=False) as source:
            content = source.read(max_bytes + 1)
        if len(content) != info.st_size:
            raise ValueError("completion draft changed while acquiring custody")
        return content
    finally:
        os.close(fd)


class CompletionDraftStore:
    """One private local owner with independently durable content and acknowledgment."""

    def __init__(self, root: Path, *, max_bytes: int):
        if type(max_bytes) is not int or max_bytes < 1:
            raise ValueError("completion draft requires a positive byte bound")
        self.root = root
        self.max_bytes = max_bytes
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = root.stat()
        if root.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("completion draft root has foreign file custody")
        _sync_directory(root.parent)

    @contextmanager
    def _owner(self):
        fd = os.open(
            self.root / "OWNER", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600
        )
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError("completion draft owner has foreign file custody")
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def _atomic(self, name: str, content: bytes) -> None:
        temporary = self.root / ("pending-" + uuid4().hex)
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as sink:
                sink.write(content)
                sink.flush()
                os.fsync(sink.fileno())
            temporary.replace(self.root / name)
            _sync_directory(self.root)
        finally:
            temporary.unlink(missing_ok=True)

    def acknowledge(
        self,
        request: Mapping[str, Any],
        *,
        release_id: str,
        operation: str,
        basis: bytes,
        check_active: Callable[[], None],
    ) -> CompletionDraft:
        """Persist the original complete request before acknowledging it to its caller."""
        if not release_id or operation not in SUPPORTED_OPERATIONS:
            raise ValueError(
                "completion draft requires its original release and supported operation"
            )
        validate_wire_schema(wire_contracts()["retain_data_completion_intent"]["input"], request)
        content = json_bytes(dict(request))
        if len(content) > self.max_bytes or len(basis) > self.max_bytes:
            raise ValueError("completion draft exceeds its byte bound")
        # Canonical bytes retain every supplied producing determinant without narrowing it.
        basis = json_bytes(wire_json_loads(basis))
        envelope = json_bytes(
            dict(
                format="ddo-completion-draft-v1",
                release_id=release_id,
                operation=operation,
                basis=wire_json_loads(basis),
                request_sha256=sha256(content).hexdigest(),
                request_bytes=len(content),
            )
        )
        if len(envelope) > self.max_bytes:
            raise ValueError("completion draft envelope exceeds its byte bound")
        identity = sha256(envelope).hexdigest()
        with self._owner():
            check_active()
            if (self.root / (identity + ".ack")).exists():
                return self._open(identity)
            self._atomic(identity + ".body", content)
            lookup = sha256(
                json_bytes(
                    {"request_id": request["request_id"], "generation": request["generation"]}
                )
            ).hexdigest()
            self._atomic(lookup + "." + identity + ".candidate", b"")
            check_active()
            self._atomic(identity + ".ack", envelope)
            return self._open(identity)

    def _open(self, identity: str) -> CompletionDraft:
        identity = _identity(identity)
        envelope = _read(self.root / (identity + ".ack"), max_bytes=self.max_bytes)
        if sha256(envelope).hexdigest() != identity:
            raise ValueError("completion acknowledgment differs from its content identity")
        value = wire_json_loads(envelope)
        if (
            set(value)
            != {"format", "release_id", "operation", "basis", "request_sha256", "request_bytes"}
            or value["format"] != "ddo-completion-draft-v1"
        ):
            raise ValueError("unsupported private completion draft")
        request = _read(
            self.root / (identity + ".body"),
            max_bytes=self.max_bytes,
            expected_bytes=value["request_bytes"],
        )
        if sha256(request).hexdigest() != value["request_sha256"]:
            raise ValueError("completion draft differs from its acknowledged body")
        validate_wire_schema(
            wire_contracts()["retain_data_completion_intent"]["input"], wire_json_loads(request)
        )
        return CompletionDraft(
            identity, value["release_id"], value["operation"], json_bytes(value["basis"]), request
        )

    def open(self, identity: str) -> CompletionDraft:
        with self._owner():
            return self._open(identity)

    def candidates(self, request_id: str, generation: int) -> Iterator[CompletionDraft]:
        """Read acknowledged original candidates before native applicability checks."""
        lookup = sha256(
            json_bytes({"request_id": request_id, "generation": generation})
        ).hexdigest()
        with self._owner():
            candidates = tuple(sorted(self.root.glob(lookup + ".*.candidate")))
        for path in candidates:
            with self._owner():
                identity = _identity(path.name.split(".")[1])
                if not (self.root / (identity + ".ack")).exists():
                    continue
                draft = self._open(identity)
                original = draft.native_request()
                if (original["request_id"], original["generation"]) != (request_id, generation):
                    raise ValueError("completion candidate differs from the selected request")
            yield draft
