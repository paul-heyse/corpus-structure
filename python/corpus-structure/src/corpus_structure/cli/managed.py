"""Checkout- or deployment-owned invocation results."""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import stat
import tempfile
import time
from collections.abc import Generator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Annotated, Any, BinaryIO, Literal
from uuid import uuid4

import typer
from pydantic import BaseModel, Field

from corpus_structure.cli.output import JsonOpt, diagnostic, emit, safe_text, state
from corpus_structure.cli.recipes import RecipeError, checkout
from corpus_structure.core.db.store import EffectKnowledge
from corpus_structure.semantic.storage_target import StorageTarget

_ID = re.compile(r"[a-f0-9]{32}")
_ROLE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")
_TERMINAL = frozenset({"passed", "failed", "interrupted", "blocked", "empty"})
_RECOVERY = ".recovery"
_OWNER = ".owner.json"
_PUBLICATIONS = ".publications.json"
_MANIFEST = "manifest.json"
_NOFOLLOW = os.O_NOFOLLOW | os.O_NONBLOCK
app = typer.Typer(help="Inspect and deliver managed invocation results.")


class OperationFailure(BaseModel):
    kind: Literal["refusal", "execution"]
    code: str
    message: str
    reason: str | None = None
    database_effects: EffectKnowledge | None = None


class RoutingProgress(BaseModel):
    nomination_run_id: int
    group_run_ids: tuple[int, ...] = ()


class OperationAccount(BaseModel):
    """Durable effects and the extent of what the owner has verified."""

    version: Literal[1] = 1
    outcome: Literal["running", "passed", "failed", "interrupted", "blocked", "empty"]
    cleanup: Literal["unknown", "unresolved", "established"]
    failure: OperationFailure | None = None
    known_effects: tuple[str, ...] | None = None
    acquired_target: StorageTarget | None = None
    predecessor: str | None = None
    reached_revision: str | None = None
    release: str | None = None
    routing: RoutingProgress | None = None


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
    operation_account: OperationAccount | None = None

    def custody_settled(self) -> bool:
        if self.settled is None or self.details.get("custody_unsettled"):
            return False
        return self.operation_account is None or self.operation_account.cleanup == "established"

    def expiry(self) -> float:
        days = 1 if self.outcome == "passed" else 7
        return (self.started if self.settled is None else self.settled) + days * 86400

    def artifact_role(self, role: str | None) -> str:
        if role is not None:
            return role
        if "bundle" in self.artifacts:
            return "bundle"
        if len(self.artifacts) == 1:
            return next(iter(self.artifacts))
        raise ResultError("select one named artifact with --role")


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


class Diagnostics(BaseModel):
    availability: Literal["available", "unavailable"] = "unavailable"
    corrupt: bool = False
    truncated: bool = False
    counts: dict[str, int] = Field(default_factory=dict)
    lane_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    missing_lanes: list[str] = Field(default_factory=list)


class ResultStatus(Manifest):
    expires_at: float | None
    custody: Literal["settled", "unsettled"]
    next_action: str | None
    diagnostics: Diagnostics


class ResultError(ValueError):
    """Unavailable, invalid or contested result."""


@contextmanager
def _directory_fd(path: Path) -> Generator[int]:
    """Anchor the directory in the canonical path without following substituted links."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            opened = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = opened
        yield fd
    finally:
        os.close(fd)


def _identity(fd: int) -> tuple[int, int]:
    info = os.fstat(fd)
    return info.st_dev, info.st_ino


def _read_file(fd: int, name: str) -> bytes:
    with os.fdopen(os.open(name, os.O_RDONLY | _NOFOLLOW, dir_fd=fd), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ResultError("managed metadata must be a regular file")
        return stream.read()


def _write_file(fd: int, name: str, content: bytes) -> None:
    temporary = f".tmp-{uuid4().hex}"
    try:
        handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=fd)
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.replace(temporary, name, src_dir_fd=fd, dst_dir_fd=fd)
    finally:
        with suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=fd)


def _open_lock(fd: int, name: str, *, create: bool = False) -> BinaryIO:
    flags = os.O_WRONLY | os.O_APPEND | _NOFOLLOW
    if create:
        flags |= os.O_CREAT
    stream = os.fdopen(os.open(name, flags, 0o600, dir_fd=fd), "ab")
    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
        stream.close()
        raise ResultError("managed lock must be a regular file")
    return stream


class Owner(BaseModel):
    id: str
    identity: tuple[int, int]


def _matches_owner(raw: bytes, result_id: str, identity: tuple[int, int]) -> bool:
    return Owner.model_validate_json(raw) == Owner(id=result_id, identity=identity)


class Publication(BaseModel):
    path: str
    identity: tuple[int, int]


class Publications(BaseModel):
    roles: dict[str, Publication] = Field(default_factory=dict)


@contextmanager
def _artifact_fd(directory: Path, relative: str) -> Generator[int]:
    path = Path(relative)
    if (
        not path.parts
        or path.is_absolute()
        or ".." in path.parts
        or path.as_posix() != relative
        or any(part.startswith(".") for part in path.parts)
        or path.parts[0] == _MANIFEST
    ):
        raise ResultError("artifact must be a named entry inside the invocation workspace")
    try:
        with _directory_fd(directory / path.parent) as parent:
            fd = os.open(path.name, os.O_RDONLY | _NOFOLLOW, dir_fd=parent)
    except OSError as error:
        raise ResultError("artifact is unavailable or substituted inside its workspace") from error
    try:
        mode = os.fstat(fd).st_mode
        if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ResultError("artifact must be a regular file or directory")
        yield fd
    finally:
        os.close(fd)


def _publication_records(fd: int) -> Publications:
    try:
        return Publications.model_validate_json(_read_file(fd, _PUBLICATIONS))
    except (OSError, ValueError) as error:
        raise ResultError("result publication records are unavailable or invalid") from error


class Invocation:
    def __init__(self, directory: Path, manifest: Manifest):
        self.directory = directory
        self.manifest = manifest

    @property
    def id(self) -> str:
        return self.manifest.id

    def _write(self) -> None:
        with _directory_fd(self.directory) as fd:
            _write_file(fd, _MANIFEST, self.manifest.model_dump_json().encode())

    def stage(self, name: str, **details: Any) -> None:
        self.manifest.stage = name
        self.manifest.details.update(details)
        self._write()

    def publish(self, role: str, path: Path) -> None:
        if not _ROLE.fullmatch(role):
            raise ResultError("invalid artifact role")
        path = path.absolute()
        if not path.is_relative_to(self.directory):
            raise ResultError("artifact must be inside the invocation workspace")
        relative = path.relative_to(self.directory).as_posix()
        with (
            _directory_fd(self.directory) as directory,
            _artifact_fd(self.directory, relative) as artifact,
        ):
            publications = _publication_records(directory)
            registration = Publication(path=relative, identity=_identity(artifact))
            if role in publications.roles and publications.roles[role] != registration:
                raise ResultError("artifact role already has a different publication")
            publications.roles[role] = registration
            _write_file(directory, _PUBLICATIONS, publications.model_dump_json().encode())
        self.manifest.artifacts[role] = relative
        self._write()

    def _update_account(self, **fields: Any) -> None:
        account = self.manifest.operation_account
        if account is not None:
            self.manifest.operation_account = account.model_copy(update=fields)

    def record_effect(self, effect: str, *, stage: str | None = None, **details: Any) -> None:
        account = self.manifest.operation_account
        assert account is not None and account.known_effects is not None
        self._update_account(known_effects=(*account.known_effects, effect))
        self.stage(stage or self.manifest.stage, **details)

    def record_target(
        self,
        target: StorageTarget,
        predecessor: str | None,
        reached_revision: str | None,
        release: str | None,
    ) -> None:
        self._update_account(
            acquired_target=target,
            predecessor=predecessor,
            reached_revision=reached_revision,
            release=release,
        )
        self._write()

    def record_routing(self, nomination_run_id: int, group_run_ids: tuple[int, ...] = ()) -> None:
        account = self.manifest.operation_account
        assert account is not None
        previous = account.routing
        if previous is not None and (
            previous.nomination_run_id != nomination_run_id
            or group_run_ids[: len(previous.group_run_ids)] != previous.group_run_ids
        ):
            raise ResultError("routing progress differs from the recorded nomination or groups")
        self._update_account(
            routing=RoutingProgress(
                nomination_run_id=nomination_run_id, group_run_ids=group_run_ids
            )
        )
        self._write()

    def record_failure(
        self, kind: Literal["refusal", "execution"], detail: dict[str, Any]
    ) -> dict[str, Any]:
        # Redact the complete string before bounding it so clipping cannot expose a credential.
        reason = detail.get("reason")
        native = detail.get("failure") or {}
        effects = native.get("effects")
        self._update_account(
            failure=OperationFailure(
                kind=kind,
                code=safe_text(detail["code"])[:128],
                message=safe_text(detail["message"])[:1024],
                reason=safe_text(reason)[:256] if isinstance(reason, str) else None,
                database_effects=EffectKnowledge(effects)
                if effects in tuple(EffectKnowledge)
                else None,
            )
        )
        self.settle("failed", error_type=self.manifest.details.get("error_type", detail["code"]))
        assert self.manifest.operation_account is not None
        return {
            "invocation_id": self.id,
            "operation_account": self.manifest.operation_account.model_dump(mode="json"),
        }

    def defer_settlement(self) -> None:
        """Protect the result while its child ownership is unresolved."""
        self.manifest.details["custody_unsettled"] = True
        self._update_account(cleanup="unresolved")
        self._write()

    def confirm_settlement(self) -> None:
        self.manifest.details.pop("custody_unsettled", None)
        self._update_account(cleanup="established")
        self._write()

    def settle(self, outcome: str = "passed", **details: Any) -> None:
        if outcome not in _TERMINAL:
            raise ResultError(f"invalid terminal outcome: {outcome}")
        self.manifest.outcome = outcome
        self.manifest.settled = time.time()
        self.manifest.details = {**self.manifest.details, **details}
        self._update_account(
            outcome=outcome,
            cleanup="unresolved"
            if self.manifest.details.get("custody_unsettled")
            else "established",
        )
        self._write()


class ResultStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    @contextmanager
    def _namespace(self) -> Generator[int]:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with _directory_fd(self.root) as root:
            info = os.fstat(root)
            if info.st_uid != os.geteuid() or info.st_mode & 0o022:
                raise ResultError("managed results root must be writable only by its operator")
            with _open_lock(root, ".namespace", create=True) as stream:
                fcntl.flock(stream, fcntl.LOCK_EX)
                yield root

    def _directory(self, result_id: str) -> Path:
        if not _ID.fullmatch(result_id):
            raise ResultError("invalid result ID")
        directory = self.root / result_id
        if directory.is_symlink() or not directory.is_dir():
            raise ResultError("result unavailable or expired")
        return directory

    @contextmanager
    def _owned_directory(self, result_id: str) -> Generator[int]:
        directory = self._directory(result_id)
        with _directory_fd(directory) as fd:
            try:
                owner = _read_file(fd, _OWNER)
                matches = _matches_owner(owner, result_id, _identity(fd))
            except FileNotFoundError as error:
                raise ResultError(
                    "result has no owner registration; import supported retained evidence by ID"
                ) from error
            except (OSError, ValueError) as error:
                raise ResultError("result workspace ownership is invalid") from error
            if not matches:
                raise ResultError("result workspace ownership changed")
            yield fd

    @contextmanager
    def lease(self, result_id: str) -> Generator[None]:
        # Open and acquire while the namespace is locked. GC never unlinks a lock
        # inode with a pending opener and never waits for a live reader or producer.
        with self._namespace():
            with self._owned_directory(result_id) as directory:
                stream = _open_lock(directory, ".lease")
            try:
                fcntl.flock(stream, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BaseException:
                stream.close()
                raise
        with stream:
            yield

    @contextmanager
    def operation(
        self, action: str, *, scope: dict[str, Any] | None = None, account: bool = False
    ) -> Generator[Invocation]:
        manifest = Manifest(id=uuid4().hex, action=action, scope=scope or {}, started=time.time())
        if account:
            manifest.operation_account = OperationAccount(
                outcome="running", cleanup="unknown", known_effects=()
            )
        directory = self.root / manifest.id
        with self._namespace() as root:
            os.mkdir(manifest.id, mode=0o700, dir_fd=root)
            with _directory_fd(directory) as fd:
                owner = Owner(id=manifest.id, identity=_identity(fd))
                _write_file(fd, _OWNER, owner.model_dump_json().encode())
                _write_file(fd, _PUBLICATIONS, Publications().model_dump_json().encode())
                stream = _open_lock(fd, ".lease", create=True)
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
                    if account and outcome == "failed":
                        result.record_failure(
                            "execution",
                            {"code": type(error).__name__, "message": "operation failed"},
                        )
                    else:
                        result.settle(outcome, error_type=type(error).__name__)
                raise
            else:
                if manifest.outcome == "running":
                    result.settle()

    @contextmanager
    def recovery_operation(
        self, action: str, source_id: str, *, source_role: str, account: bool = False
    ) -> Generator[Invocation]:
        """Keep an exact source usable while a dependent may still need recovery."""
        with (
            self.lease(source_id),
            self.operation(action, scope={source_role: source_id}, account=account) as result,
        ):
            with self._namespace():
                self._dependency_source(source_id)
                self._write_hold(source_id, _RECOVERY, result.id)
            yield result
            if result.manifest.outcome in {"running", "passed"}:
                with self._namespace():
                    self._remove_hold(source_id, _RECOVERY, result.id)

    def _read(self, directory: Path, *, role: str | None = None) -> Manifest:
        try:
            with self._owned_directory(directory.name) as fd:
                manifest = Manifest.model_validate_json(_read_file(fd, _MANIFEST))
                registered = _publication_records(fd).roles
        except (OSError, ValueError) as error:
            if isinstance(error, ResultError):
                raise
            raise ResultError("result manifest unavailable or invalid") from error
        if manifest.id != directory.name:
            raise ResultError("result identity does not match its workspace")
        for name, path in manifest.artifacts.items():
            if role is not None and role != name:
                continue
            if name not in registered or registered[name].path != path:
                raise ResultError("artifact selection differs from its owner publication")
            with _artifact_fd(directory, path) as artifact:
                if registered[name].identity != _identity(artifact):
                    raise ResultError("artifact differs from its owner publication")
        manifest.holds = tuple(_hold_ids(directory, ".holds"))
        return manifest

    def show(self, result_id: str, *, role: str | None = None) -> Manifest:
        """Inspect the result, authenticating only the selected publication when specified."""
        with self.lease(result_id):
            return self._inspection(self._directory(result_id), role=role)

    def _inspection(self, directory: Path, *, role: str | None = None) -> Manifest:
        manifest = self._read(directory, role=role)
        recovery_holds = self._recovery_holds(directory, time.time())
        manifest.holds = tuple(sorted(set(manifest.holds).union(recovery_holds)))
        return manifest

    @contextmanager
    def _exclusive(self, result_id: str, *, importing: bool = False) -> Generator[Path]:
        owner_directory = (
            _directory_fd(self._directory(result_id))
            if importing
            else self._owned_directory(result_id)
        )
        with self._namespace(), owner_directory as fd:
            lease = _open_lock(fd, ".lease")
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                lease.close()
                raise ResultError(
                    "result is in use; retry after its owner or readers settle"
                ) from error
        with lease:
            yield self._directory(result_id)

    def recover(self, result_id: str) -> Manifest:
        with self._exclusive(result_id) as directory:
            manifest = self._read(directory)
            if manifest.settled is not None and not manifest.details.get("custody_unsettled"):
                return manifest
            invocation = Invocation(directory, manifest)
            if manifest.action not in {"test", "test.retry"} or manifest.stage not in _TEST_LANES:
                raise ResultError(
                    "settlement is unproven; inspect the owning operation and retain this workspace"
                )
            lane = manifest.stage
            _require_drained_test_lane(directory / lane, lane)
            from corpus_structure.cli.testing import _supervisor

            receipt = directory / lane
            next_action = f"ci test --lane {lane}"
            with suppress(RecipeError, ResultError), _artifact_fd(directory, lane) as fd:
                classification = _supervisor(
                    "classify", "--summary", "--receipt-dir", str(receipt), opened={receipt: fd}
                )
                if classification["retryable"]:
                    next_action = f"ci test retry {result_id} --lane {lane}"
            invocation.publish(lane, directory / lane)
            invocation.confirm_settlement()
            invocation.settle(
                "interrupted",
                next_action=next_action,
                recovered_lane=lane,
            )
            return manifest

    def import_test(self, result_id: str) -> Manifest:
        """Register an exact older test receipt as evidence under its existing ID."""
        with (
            self._exclusive(result_id, importing=True) as directory,
            _directory_fd(directory) as fd,
        ):
            if os.path.lexists(directory / _OWNER):
                return self._read(directory)
            manifest = Manifest.model_validate_json(_read_file(fd, _MANIFEST))
            if (
                manifest.id != result_id
                or manifest.action not in {"test", "test.retry"}
                or manifest.outcome not in _TERMINAL
                or manifest.settled is None
                or manifest.details.get("custody_unsettled")
                or not manifest.artifacts
                or any(
                    role not in _TEST_LANES or role != path
                    for role, path in manifest.artifacts.items()
                )
            ):
                raise ResultError("only settled, owner-verifiable test receipts may be imported")
            publications = Publications()
            for lane in manifest.artifacts:
                _require_drained_test_lane(directory / lane, lane)
                with _artifact_fd(directory, lane) as entry:
                    publications.roles[lane] = Publication(path=lane, identity=_identity(entry))
            from corpus_structure.cli.testing import _supervisor

            args = [
                token
                for lane in manifest.artifacts
                for token in ("--receipt-dir", str(directory / lane))
            ]
            classification = _supervisor("classify", "--summary", *args)
            contexts = classification["contexts"]
            if len(contexts) != len(manifest.artifacts) or any(
                context["invocation"] is None for context in contexts
            ):
                raise ResultError("supervisor did not verify the imported receipt context")
            _write_file(fd, _PUBLICATIONS, publications.model_dump_json().encode())
            owner = Owner(id=result_id, identity=_identity(fd))
            _write_file(fd, _OWNER, owner.model_dump_json().encode())
            return self._read(directory)

    def hold(self, result_id: str, dependent_id: str) -> None:
        if not _ID.fullmatch(dependent_id):
            raise ResultError("invalid dependent ID")
        with self._namespace():
            self._dependency_source(result_id)
            self._write_hold(result_id, ".holds", dependent_id)

    def _write_hold(self, result_id: str, kind: str, dependent_id: str) -> None:
        with self._owned_directory(result_id) as owner:
            with suppress(FileExistsError):
                os.mkdir(kind, mode=0o700, dir_fd=owner)
            with _directory_fd(self.root / result_id / kind) as holds:
                _write_file(holds, dependent_id, b"")

    def _remove_hold(self, result_id: str, kind: str, dependent_id: str) -> None:
        with (
            self._owned_directory(result_id),
            suppress(FileNotFoundError),
            _directory_fd(self.root / result_id / kind) as holds,
        ):
            os.unlink(dependent_id, dir_fd=holds)

    def _dependency_source(self, result_id: str) -> Path:
        directory = self._directory(result_id)
        manifest = self._read(directory)
        now = time.time()
        if (
            manifest.settled is not None
            and now >= manifest.expiry()
            and not manifest.details.get("custody_unsettled")
            and not _hold_ids(directory, ".holds")
            and not self._needs_recovery(directory, now)
        ):
            raise ResultError("result has expired; select a current result for the dependency")
        return directory

    def dependency_available(self, result_id: str) -> bool:
        """Observe current eligibility without acquiring a dependency or hold."""
        try:
            self._dependency_source(result_id)
        except ResultError:
            return False
        return True

    def release(self, result_id: str, dependent_id: str) -> None:
        if not _ID.fullmatch(dependent_id):
            raise ResultError("invalid dependent ID")
        with self._namespace():
            self._remove_hold(result_id, ".holds", dependent_id)

    def _needs_recovery(self, directory: Path, now: float) -> bool:
        return next(self._recovery_holds(directory, now), None) is not None

    def _recovery_holds(self, directory: Path, now: float) -> Generator[str]:
        for dependent_id in _hold_ids(directory, _RECOVERY):
            try:
                dependent = self._directory(dependent_id)
            except ResultError:
                continue
            manifest = self._read(dependent)
            if manifest.outcome == "passed":
                continue
            if (
                manifest.settled is None
                or manifest.details.get("custody_unsettled")
                or now < manifest.expiry()
            ):
                yield dependent_id

    @contextmanager
    def open_artifact(self, result_id: str, role: str) -> Generator[tuple[Path, int]]:
        """Borrow an authenticated publication for an owned read."""
        directory = self._directory(result_id)
        manifest = self._read(directory, role=role)
        if manifest.settled is None or role not in manifest.artifacts:
            raise ResultError("settled artifact unavailable")
        relative = manifest.artifacts[role]
        with self._owned_directory(result_id) as owned, _artifact_fd(directory, relative) as fd:
            record = _publication_records(owned).roles.get(role)
            if record is None or record.path != relative or record.identity != _identity(fd):
                raise ResultError("artifact differs from its owner publication")
            yield directory / relative, fd

    def artifact(self, result_id: str, role: str) -> Path:
        with self.open_artifact(result_id, role) as (source, _):
            return source

    def read_artifact(self, result_id: str, role: str) -> bytes:
        with self.open_artifact(result_id, role) as (_, fd):
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ResultError("managed artifact must be a regular file")
            with os.fdopen(os.dup(fd), "rb") as stream:
                return stream.read()

    def deliver(self, result_id: str, role: str | None, destination: Path | None) -> Path:
        with self.lease(result_id):
            manifest = self.show(result_id)
            with self.open_artifact(result_id, manifest.artifact_role(role)) as (source, fd):
                if destination is None:
                    return source
                destination = destination.parent.resolve() / destination.name
                if destination.is_relative_to(self.root):
                    raise ResultError("delivery destination must be outside managed storage")
                _deliver_entry(fd, destination)
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
        for name in sorted(os.listdir(self.root)):
            result_id = name.removeprefix(".gc-")
            if not _ID.fullmatch(result_id):
                continue
            with self._namespace() as root:
                retired = f".gc-{result_id}"
                marker = f".retire-{result_id}.json"
                if name == retired:
                    try:
                        with _directory_fd(self.root / retired) as target:
                            if not _matches_owner(
                                _read_file(root, marker), result_id, _identity(target)
                            ):
                                continue
                    except OSError, ValueError:
                        continue
                    result.eligible.append(result_id)
                    if apply:
                        shutil.rmtree(retired, dir_fd=root)
                        os.unlink(marker, dir_fd=root)
                        result.removed.append(result_id)
                    continue
                try:
                    directory = self.root / result_id
                    with self._owned_directory(result_id) as fd, _open_lock(fd, ".lease") as lease:
                        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        manifest = self._read(directory)
                        if (
                            manifest.settled is None
                            or manifest.details.get("custody_unsettled")
                            or timestamp < manifest.expiry()
                            or _hold_ids(directory, ".holds")
                            or self._needs_recovery(directory, timestamp)
                            or os.path.lexists(self.root / retired)
                        ):
                            continue
                        if apply:
                            from corpus_structure.serve.companion_export import _publish_directory

                            owner = Owner(id=result_id, identity=_identity(fd))
                            _write_file(root, marker, owner.model_dump_json().encode())
                            anchored = Path(f"/proc/self/fd/{root}")
                            _publish_directory(anchored / result_id, anchored / retired)
                            shutil.rmtree(retired, dir_fd=root)
                            os.unlink(marker, dir_fd=root)
                            result.removed.append(result_id)
                        result.eligible.append(result_id)
                except BlockingIOError, FileNotFoundError, ResultError:
                    continue
        return result


def _hold_ids(directory: Path, kind: str) -> list[str]:
    try:
        with _directory_fd(directory / kind) as fd:
            return sorted(
                name
                for name in os.listdir(fd)
                if _ID.fullmatch(name)
                and stat.S_ISREG(os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode)
            )
    except FileNotFoundError:
        return []


def _copy_entry(fd: int, destination: Path) -> None:
    mode = os.fstat(fd).st_mode
    if stat.S_ISREG(mode):
        with os.fdopen(os.dup(fd), "rb") as source, destination.open("xb") as output:
            shutil.copyfileobj(source, output)
    elif stat.S_ISDIR(mode):
        destination.mkdir(mode=0o700)
        for name in os.listdir(fd):
            child = os.open(name, os.O_RDONLY | _NOFOLLOW, dir_fd=fd)
            try:
                _copy_entry(child, destination / name)
            finally:
                os.close(child)
    else:
        raise ResultError("bundle contains a special file")


def _deliver_entry(fd: int, destination: Path) -> None:
    with tempfile.TemporaryDirectory(dir=destination.parent) as staging:
        staged = Path(staging) / "artifact"
        _copy_entry(fd, staged)
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            from corpus_structure.serve.companion_export import _publish_directory

            _publish_directory(staged, destination)
        else:
            os.link(staged, destination)


_TEST_LANES = ("ordinary", "fault")


def _require_drained_test_lane(directory: Path, lane: str) -> None:
    try:
        with _directory_fd(directory) as fd:
            invocation = json.loads(_read_file(fd, "invocation.json"))
            runner = json.loads(_read_file(fd, "runner.process.json"))
            classification = os.stat("classification.json", dir_fd=fd, follow_symlinks=False)
            argv = invocation["argv"]
            if (
                invocation["managed_lane"] != lane
                or argv[argv.index("--out-dir") + 1] != str(directory)
                or not runner.get("finished")
                or not stat.S_ISREG(classification.st_mode)
            ):
                raise ValueError("lane was not finalized by its supervisor")
            processes = {"pytest.process.json"}
            processes.update(
                name
                for name in os.listdir(fd)
                if name.endswith(".process.json") and name != "runner.process.json"
            )
            for name in processes:
                process = json.loads(_read_file(fd, name))
                cleanup = process.get("owned_group_cleanup") or {}
                if (
                    not process.get("finished")
                    or process.get("cleanup_error")
                    or cleanup.get("group_present_after_cleanup") is not False
                ):
                    raise ValueError("a supervisor child group has no settlement proof")
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        raise ResultError(
            "test settlement is unproven; inspect the supervisor receipt before retrying"
        ) from error


@contextmanager
def managed_operation(
    store: ResultStore,
    action: str,
    *,
    json: bool,
    expected: tuple[type[Exception], ...] = (),
    source: tuple[str, str] | None = None,
    scope: dict[str, Any] | None = None,
) -> Generator[Invocation]:
    """Keep immediate failure delivery and its managed account at one boundary."""
    from corpus_structure.cli.failures import failure_boundary

    context = (
        store.operation(action, scope=scope, account=True)
        if source is None
        else store.recovery_operation(action, source[1], source_role=source[0], account=True)
    )
    expected = (ResultError, *expected)
    with (
        failure_boundary(json, expected=expected),
        context as result,
        failure_boundary(json, expected=expected, operation=result),
    ):
        yield result


def result_store(ctx: typer.Context) -> ResultStore:
    override = state(ctx).settings().ci_results
    if override is not None:
        if not override.is_absolute():
            raise ResultError("CORPUS_CI_RESULTS must be an absolute path")
        return ResultStore(override)
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

    with failure_boundary(
        json, expected=(ResultError, RecipeError, OSError), report_expected_validation=False
    ):
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
        store = result_store(ctx)
        with store.lease(result):
            directory = store._directory(result)
            manifest = store._inspection(directory)
            diagnostics = Diagnostics()
            for lane in _diagnostic_lanes(manifest):
                _receipt_events(
                    store,
                    directory,
                    manifest,
                    lane,
                    diagnostics,
                    None,
                    settled=manifest.settled is not None,
                )
            emit(_status(manifest, diagnostics), json=json)


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
        lane_counts: dict[str, dict[str, int]] = {}
        cursors: dict[str, tuple[int, bool]] = {}
        diagnostics = Diagnostics()
        with store.lease(result):
            directory = store._directory(result)
            while True:
                item = store._inspection(directory)
                if item.stage != stage:
                    if item.settled is None and seconds:
                        diagnostic(f"Result {result} · {item.stage}")
                    stage = item.stage
                if seconds:
                    for lane in _diagnostic_lanes(item):
                        counts = item.details.get("lane_counts", {}).get(lane)
                        if counts and counts != lane_counts.get(lane):
                            lane_counts[lane] = counts
                            summary = ", ".join(
                                f"{key}={counts[key]}"
                                for key in ("selected", "passed", "failed", "blocked", "skipped")
                                if type(counts.get(key)) is int
                            )
                            if summary:
                                diagnostic(f"Result {result} · {lane} · {summary}")
                done = item.settled is not None or time.monotonic() >= deadline
                for lane in _diagnostic_lanes(item):
                    cursors[lane] = _receipt_events(
                        store,
                        directory,
                        item,
                        lane,
                        diagnostics,
                        cursors.get(lane, (0, False)),
                        settled=item.settled is not None or lane in item.artifacts,
                        final=done,
                        announce=True,
                    )
                if done:
                    emit(_status(item, diagnostics), json=json)
                    return
                time.sleep(0.2)


def _status(manifest: Manifest, diagnostics: Diagnostics) -> ResultStatus:
    unsettled = not manifest.custody_settled()
    next_action = manifest.details.get("next_action")
    if unsettled and manifest.action in {"test", "test.retry"} and manifest.stage in _TEST_LANES:
        next_action = (
            f"ci results watch {manifest.id}; after exit, ci results recover {manifest.id}"
            if manifest.settled is None
            else f"ci results recover {manifest.id}"
        )
    elif unsettled:
        next_action = "Inspect the owning operation and retain this workspace until settlement."
    diagnostics.lane_counts = manifest.details.get("lane_counts", {})
    return ResultStatus(
        **manifest.model_dump(),
        expires_at=None if unsettled or manifest.holds else manifest.expiry(),
        custody="unsettled" if unsettled else "settled",
        next_action=next_action,
        diagnostics=diagnostics,
    )


def _diagnostic_lanes(manifest: Manifest) -> list[str]:
    if manifest.action not in {"test", "test.retry"}:
        return []
    return [
        lane
        for lane in _TEST_LANES
        if lane in manifest.artifacts
        or lane == manifest.stage
        or lane in manifest.scope.get("required_lanes", ())
        or lane in manifest.details.get("lanes", {})
    ]


_DIAGNOSTIC_BYTES = 65536


@contextmanager
def _reportlog_fd(
    store: ResultStore, directory: Path, manifest: Manifest, lane: str
) -> Generator[int]:
    if manifest.settled is not None and lane in manifest.artifacts:
        with store.open_artifact(manifest.id, lane) as (_, parent):
            fd = os.open("reportlog.jsonl", os.O_RDONLY | _NOFOLLOW, dir_fd=parent)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise ResultError("managed reportlog must be a regular file")
                yield fd
            finally:
                os.close(fd)
    else:
        with _artifact_fd(directory, f"{lane}/reportlog.jsonl") as fd:
            yield fd


def _receipt_events(
    store: ResultStore,
    directory: Path,
    manifest: Manifest,
    lane: str,
    diagnostics: Diagnostics,
    cursor: tuple[int, bool] | None,
    *,
    settled: bool,
    final: bool = True,
    announce: bool = False,
) -> tuple[int, bool]:
    offset, discarding = cursor or (0, False)
    try:
        with (
            _reportlog_fd(store, directory, manifest, lane) as fd,
            os.fdopen(os.dup(fd), "rb") as stream,
        ):
            size = os.fstat(fd).st_size
            if final and size - offset > _DIAGNOSTIC_BYTES:
                offset, discarding = size - _DIAGNOSTIC_BYTES, True
                diagnostics.truncated = True
            stream.seek(offset)
            batch = stream.read(_DIAGNOSTIC_BYTES)
    except OSError, ResultError:
        if lane not in diagnostics.missing_lanes:
            diagnostics.missing_lanes.append(lane)
        return offset, discarding
    diagnostics.availability = "available"
    if lane in diagnostics.missing_lanes:
        diagnostics.missing_lanes.remove(lane)
    at_end = offset + len(batch) >= size
    if final and not at_end:
        diagnostics.truncated = True
    if discarding:
        end = batch.find(b"\n")
        if end < 0:
            return offset + len(batch), True
        offset += end + 1
        batch = batch[end + 1 :]
    last = batch.rfind(b"\n")
    if settled and at_end and len(batch) > last + 1:
        diagnostics.corrupt = True
    if last < 0:
        if len(batch) == _DIAGNOSTIC_BYTES:
            diagnostics.truncated = True
            return offset + len(batch), True
        return offset, False
    announced = 0
    for raw in batch[:last].splitlines():
        try:
            event = json.loads(raw)
        except ValueError:
            diagnostics.corrupt = True
            continue
        if not isinstance(event, dict):
            diagnostics.corrupt = True
            continue
        outcome = event.get("outcome")
        if not isinstance(outcome, str) or outcome not in {"passed", "failed", "skipped"}:
            continue
        if event.get("when") == "call" or outcome == "failed":
            key = f"{lane}.{outcome}"
            diagnostics.counts[key] = diagnostics.counts.get(key, 0) + 1
        if announce and outcome == "failed" and announced < 8:
            diagnostic(f"Failed: {event.get('nodeid', 'test')}")
            announced += 1
    return offset + last + 1, False


@app.command("recover")
def recover_result(ctx: typer.Context, result: str, json: JsonOpt = False) -> None:
    """Settle an abandoned result with a drained supervisor receipt."""
    with result_boundary(json):
        emit(result_store(ctx).recover(result), json=json)


@app.command("import")
def import_result(ctx: typer.Context, result: str, json: JsonOpt = False) -> None:
    """Register a retained test receipt under its original result identity."""
    with result_boundary(json):
        emit(result_store(ctx).import_test(result), json=json)


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
