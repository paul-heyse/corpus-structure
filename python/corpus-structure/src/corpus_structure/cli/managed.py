"""Checkout- or deployment-owned invocation results."""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import tempfile
import time
from collections.abc import Generator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Annotated, Any
from uuid import uuid4

import typer
from pydantic import BaseModel, Field

from corpus_structure.cli.output import JsonOpt, diagnostic, emit
from corpus_structure.cli.recipes import RecipeError, checkout

_ID = re.compile(r"[a-f0-9]{32}")
_TERMINAL = frozenset({"passed", "failed", "interrupted", "blocked", "empty"})
_RECOVERY = ".recovery"
app = typer.Typer(help="Inspect and deliver managed invocation results.")


class Manifest(BaseModel):
    id: str
    action: str
    scope: dict[str, Any] = Field(default_factory=dict)
    started: float
    stage: str = "starting"
    outcome: str = "running"
    settled: float | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
    holds: tuple[str, ...] = ()

    def expiry(self) -> float:
        days = 1 if self.outcome == "passed" else 7
        return (self.started if self.settled is None else self.settled) + days * 86400


class ResultList(BaseModel):
    results: list[Manifest]
    next_after: str | None = None


class Delivery(BaseModel):
    id: str
    path: Path


class Collection(BaseModel):
    eligible: list[str]
    removed: list[str]
    preview: bool


class ResultError(ValueError):
    """Unavailable, invalid or contested result."""


class Invocation:
    def __init__(self, directory: Path, manifest: Manifest):
        self.directory = directory
        self.manifest = manifest

    @property
    def id(self) -> str:
        return self.manifest.id

    def _write(self) -> None:
        with tempfile.NamedTemporaryFile(dir=self.directory, delete=False) as stream:
            stage = Path(stream.name)
            try:
                stream.write(self.manifest.model_dump_json().encode())
                stream.close()
                os.replace(stage, self.directory / "manifest.json")
            finally:
                stage.unlink(missing_ok=True)

    def stage(self, name: str, **details: Any) -> None:
        self.manifest.stage = name
        self.manifest.details.update(details)
        self._write()

    def publish(self, role: str, path: Path) -> None:
        root = self.directory.resolve()
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or resolved == root:
            raise ResultError("artifact must be inside the invocation workspace")
        relative = resolved.relative_to(root)
        if relative.parts[0] in {"manifest.json", ".holds", ".lease", _RECOVERY}:
            raise ResultError("cannot expose result bookkeeping as an artifact")
        self.manifest.artifacts[role] = relative.as_posix()
        self._write()

    def settle(self, outcome: str = "passed", **details: Any) -> None:
        if outcome not in _TERMINAL:
            raise ResultError(f"invalid terminal outcome: {outcome}")
        self.manifest.outcome = outcome
        self.manifest.settled = time.time()
        self.manifest.details = details
        self._write()


class ResultStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    @contextmanager
    def _namespace(self) -> Generator[None]:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (self.root / ".namespace").open("ab") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def _directory(self, result_id: str) -> Path:
        if not _ID.fullmatch(result_id):
            raise ResultError("invalid result ID")
        directory = self.root / result_id
        if directory.is_symlink() or not directory.is_dir():
            raise ResultError("result unavailable or expired")
        return directory

    @contextmanager
    def lease(self, result_id: str) -> Generator[None]:
        # Open and acquire while the namespace is locked. GC never unlinks a lock
        # inode with a pending opener and never waits for a live reader or producer.
        with self._namespace():
            directory = self._directory(result_id)
            stream = (directory / ".lease").open("ab")
            try:
                fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BaseException:
                stream.close()
                raise
        with stream:
            yield

    @contextmanager
    def operation(
        self, action: str, *, scope: dict[str, Any] | None = None
    ) -> Generator[Invocation]:
        manifest = Manifest(id=uuid4().hex, action=action, scope=scope or {}, started=time.time())
        directory = self.root / manifest.id
        with self._namespace():
            directory.mkdir(mode=0o700)
            stream = (directory / ".lease").open("ab")
            fcntl.flock(stream, fcntl.LOCK_SH)
        with stream:
            result = Invocation(directory, manifest)
            result._write()
            diagnostic(f"Result {manifest.id}")
            try:
                yield result
            except BaseException as error:
                if manifest.outcome == "running":
                    outcome = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
                    result.settle(
                        outcome, **{**manifest.details, "error_type": type(error).__name__}
                    )
                raise
            else:
                if manifest.outcome == "running":
                    result.settle()

    @contextmanager
    def recovery_operation(
        self, action: str, source_id: str, *, source_role: str
    ) -> Generator[Invocation]:
        """Keep an exact source usable while a dependent may still need recovery."""
        with (
            self.lease(source_id),
            self.operation(action, scope={source_role: source_id}) as result,
        ):
            with self._namespace():
                recovery = self._directory(source_id) / _RECOVERY
                recovery.mkdir(exist_ok=True, mode=0o700)
                marker = recovery / result.id
                marker.touch()
            yield result
            if result.manifest.outcome in {"running", "passed"}:
                with self._namespace():
                    marker.unlink(missing_ok=True)

    def _read(self, directory: Path) -> Manifest:
        try:
            manifest = Manifest.model_validate_json((directory / "manifest.json").read_bytes())
        except (OSError, ValueError) as error:
            raise ResultError("result manifest unavailable or invalid") from error
        if manifest.id != directory.name:
            raise ResultError("result identity does not match its workspace")
        manifest.holds = tuple(
            sorted(
                {
                    marker.name
                    for kind in (".holds", _RECOVERY)
                    for marker in (directory / kind).glob("*")
                }
            )
        )
        return manifest

    def show(self, result_id: str) -> Manifest:
        with self.lease(result_id):
            return self._read(self._directory(result_id))

    def hold(self, result_id: str, dependent_id: str) -> None:
        if not _ID.fullmatch(dependent_id):
            raise ResultError("invalid dependent ID")
        with self._namespace():
            holds = self._directory(result_id) / ".holds"
            holds.mkdir(exist_ok=True, mode=0o700)
            (holds / dependent_id).touch()

    def release(self, result_id: str, dependent_id: str) -> None:
        if not _ID.fullmatch(dependent_id):
            raise ResultError("invalid dependent ID")
        with self._namespace():
            (self._directory(result_id) / ".holds" / dependent_id).unlink(missing_ok=True)

    def _needs_recovery(self, directory: Path, now: float) -> bool:
        for marker in (directory / _RECOVERY).glob("*"):
            try:
                dependent = self._directory(marker.name)
            except ResultError:
                continue
            manifest = self._read(dependent)
            if manifest.outcome == "passed":
                continue
            if now < manifest.expiry():
                return True
            if manifest.settled is None:
                with (dependent / ".lease").open("ab") as stream:
                    try:
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        return True
        return False

    def artifact(self, result_id: str, role: str) -> Path:
        directory = self._directory(result_id)
        manifest = self._read(directory)
        if manifest.settled is None or role not in manifest.artifacts:
            raise ResultError("settled artifact unavailable")
        path = (directory / manifest.artifacts[role]).resolve()
        if not path.is_relative_to(directory) or not path.exists():
            raise ResultError("artifact is missing or outside its workspace")
        return path

    def deliver(self, result_id: str, role: str | None, destination: Path | None) -> Path:
        with self.lease(result_id):
            manifest = self.show(result_id)
            if role is None:
                if "bundle" in manifest.artifacts:
                    role = "bundle"
                elif len(manifest.artifacts) == 1:
                    role = next(iter(manifest.artifacts))
                else:
                    raise ResultError("select one named artifact with --role")
            source = self.artifact(result_id, role)
            if destination is None:
                return source
            destination = destination.parent.resolve() / destination.name
            if destination.is_relative_to(self.root):
                raise ResultError("delivery destination must be outside managed storage")
            if source.is_dir():
                from corpus_structure.serve.companion_export import _publish_directory

                with tempfile.TemporaryDirectory(dir=destination.parent) as staging:
                    copy = Path(staging) / "bundle"
                    _check_bundle(source)
                    shutil.copytree(source, copy)
                    _publish_directory(copy, destination)
            else:
                with tempfile.NamedTemporaryFile(dir=destination.parent) as staging:
                    with source.open("rb") as src:
                        shutil.copyfileobj(src, staging)
                    staging.flush()
                    os.link(staging.name, destination)
            return destination

    def list(self, after: str | None, limit: int, action: str | None) -> ResultList:
        found: list[Manifest] = []
        if not self.root.exists():
            return ResultList(results=found)
        for path in sorted(self.root.iterdir()):
            if not _ID.fullmatch(path.name) or (after is not None and path.name <= after):
                continue
            try:
                item = self.show(path.name)
            except ResultError, FileNotFoundError:
                continue
            if action is None or item.action == action:
                found.append(item)
            if len(found) > limit:
                break
        return ResultList(
            results=found[:limit], next_after=found[limit - 1].id if len(found) > limit else None
        )

    def collect(self, *, apply: bool, now: float | None = None) -> Collection:
        timestamp = time.time() if now is None else now
        result = Collection(eligible=[], removed=[], preview=not apply)
        if not self.root.is_dir():
            return result
        for directory in sorted(self.root.iterdir()):
            if directory.name.startswith(".gc-") and _ID.fullmatch(directory.name[4:]):
                if apply and directory.is_dir() and not directory.is_symlink():
                    with suppress(FileNotFoundError):
                        shutil.rmtree(directory)
                continue
            if not _ID.fullmatch(directory.name):
                continue
            retired = None
            with self._namespace():
                if directory.is_symlink() or not directory.is_dir():
                    continue
                try:
                    with (directory / ".lease").open("ab") as stream:
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        manifest = self._read(directory)
                        if (
                            manifest.settled is None
                            or manifest.details.get("custody_unsettled")
                            or timestamp < manifest.expiry()
                            or any((directory / ".holds").glob("*"))
                            or self._needs_recovery(directory, timestamp)
                        ):
                            continue
                        result.eligible.append(manifest.id)
                        if apply:
                            retired = self.root / f".gc-{manifest.id}"
                            directory.rename(retired)
                except BlockingIOError, ResultError:
                    continue
            if retired is not None:
                with suppress(FileNotFoundError):
                    shutil.rmtree(retired)
                result.removed.append(directory.name)
        return result


def _check_bundle(root: Path) -> None:
    for directory, folders, files in os.walk(root, followlinks=False):
        for name in (*folders, *files):
            path = Path(directory) / name
            if path.is_symlink() or not (path.is_dir() or path.is_file()):
                raise ResultError("bundle contains a symlink or special file")


def result_store(ctx: typer.Context) -> ResultStore:
    override = os.environ.get("CORPUS_CI_RESULTS")
    if override:
        path = Path(override)
        if not path.is_absolute():
            raise ResultError("CORPUS_CI_RESULTS must be an absolute path")
        return ResultStore(path)
    workspace = checkout(ctx)
    root = (workspace / "build" / "ci").resolve()
    if not root.is_relative_to(workspace):
        raise ResultError(
            "checkout result storage escapes the workspace; configure CORPUS_CI_RESULTS explicitly"
        )
    return ResultStore(root)


@contextmanager
def result_boundary(json: bool) -> Generator[None]:
    from corpus_structure.cli.failures import failure_boundary

    with failure_boundary(json, expected=(ResultError, RecipeError, OSError)):
        yield


@app.command("list")
def list_results(
    ctx: typer.Context,
    limit: Annotated[int, typer.Option(min=1, max=100)] = 20,
    after: str | None = None,
    action: str | None = None,
    json: JsonOpt = False,
) -> None:
    with result_boundary(json):
        emit(result_store(ctx).list(after, limit, action), json=json)


@app.command("show")
def show_result(ctx: typer.Context, result: str, json: JsonOpt = False) -> None:
    with result_boundary(json):
        emit(result_store(ctx).show(result), json=json)


@app.command("watch")
def watch_result(
    ctx: typer.Context,
    result: str,
    seconds: Annotated[float, typer.Option(min=0, max=300)] = 30,
    json: JsonOpt = False,
) -> None:
    with result_boundary(json):
        store = result_store(ctx)
        deadline = time.monotonic() + seconds
        stage = None
        cursor = (0, False)
        with store.lease(result):
            directory = store._directory(result)
            while True:
                item = store._read(directory)
                if item.stage != stage:
                    if item.settled is None and seconds:
                        diagnostic(item.stage)
                    stage, cursor = item.stage, (0, False)
                if item.settled is not None or time.monotonic() >= deadline:
                    emit(item, json=json)
                    return
                if stage in {"ordinary", "fault"}:
                    cursor = _watch_receipt(directory / stage / "reportlog.jsonl", cursor)
                time.sleep(0.2)


def _watch_receipt(path: Path, cursor: tuple[int, bool]) -> tuple[int, bool]:
    offset, discarding = cursor
    try:
        with path.open("rb") as stream:
            stream.seek(offset)
            batch = stream.read(65536)
    except FileNotFoundError:
        return cursor
    if discarding:
        end = batch.find(b"\n")
        if end < 0:
            return offset + len(batch), True
        offset += end + 1
        batch = batch[end + 1 :]
    last = batch.rfind(b"\n")
    if last < 0:
        if len(batch) == 65536:
            diagnostic("test diagnostics: oversized receipt record")
            return offset + len(batch), True
        return offset, False
    for raw in batch[:last].splitlines():
        try:
            event = json.loads(raw)
        except ValueError:
            diagnostic("test diagnostics: malformed receipt record")
            continue
        if isinstance(event, dict) and event.get("outcome") == "failed":
            diagnostic(f"Failed: {event.get('nodeid', 'test')}")
    return offset + last + 1, False


@app.command("export")
def export_result(
    ctx: typer.Context,
    result: str,
    role: str | None = None,
    destination: Path | None = None,
    json: JsonOpt = False,
) -> None:
    with result_boundary(json):
        path = result_store(ctx).deliver(result, role, destination)
        emit(Delivery(id=result, path=path), json=json)


@app.command("gc")
def gc(ctx: typer.Context, apply: bool = False, json: JsonOpt = False) -> None:
    with result_boundary(json):
        emit(result_store(ctx).collect(apply=apply), json=json)


@app.command("hold")
def hold(
    ctx: typer.Context, result: str, dependent: str | None = None, json: JsonOpt = False
) -> None:
    """Protect a result, optionally on behalf of another invocation."""
    with result_boundary(json):
        store = result_store(ctx)
        store.hold(result, dependent or result)
        emit(store.show(result), json=json)


@app.command("release-hold")
def release_hold(
    ctx: typer.Context, result: str, dependent: str | None = None, json: JsonOpt = False
) -> None:
    """Release a result's explicit hold."""
    with result_boundary(json):
        store = result_store(ctx)
        store.release(result, dependent or result)
        emit(store.show(result), json=json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="results")
