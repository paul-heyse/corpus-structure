"""Durable private completion custody before a native intent commits.

The acknowledged request keeps its original producer fence and execution evidence.
Reading a draft establishes local custody. Native settlement owns use authority.
"""

from __future__ import annotations

import fcntl
import os
import re
import stat
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryFile
from typing import TYPE_CHECKING, Any, Literal, cast
from uuid import uuid4

from .data_operation_json import finite_json_loads, json_bytes, native_json_loads
from .data_operation_wire import validate_wire_schema

if TYPE_CHECKING:
    import pyarrow as pa

    from ._data_operation_wire import (
        WireInspectDataCompletionDraftRequest,
        WireInspectDataCompletionDraftResult,
        WireRetainDataCompletionIntentRequest,
    )
    from .arrow_transfer import ArrowWriteProfile
    from .storage_target import StorageTarget


SUPPORTED_OPERATIONS = frozenset({"source.pdf/capture", "segment.sentences/source-native"})


@dataclass(frozen=True)
class PopulationUploadFile:
    """Acknowledged durable IPC acquired into private bytes before COPY consumption."""

    path: Path
    byte_length: int
    digest: str

    def _copy(self, output=None, *, check_active=lambda: None):
        check_active()
        descriptor = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.getuid()
                or before.st_size != self.byte_length
            ):
                raise ValueError("completion draft differs from its acknowledged population upload")
            digest = sha256()
            remaining = self.byte_length
            with os.fdopen(descriptor, "rb", closefd=False) as source:
                while remaining:
                    check_active()
                    chunk = source.read(min(remaining, 1024 * 1024))
                    if not chunk:
                        raise ValueError(
                            "completion population upload changed while acquiring custody"
                        )
                    digest.update(chunk)
                    if output is not None:
                        output.write(chunk)
                    remaining -= len(chunk)
            check_active()
            after = os.fstat(descriptor)
            if digest.hexdigest() != self.digest or (
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            ) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("completion draft differs from its acknowledged population upload")
        finally:
            os.close(descriptor)

    @contextmanager
    def open_reader(self, *, check_active=lambda: None):
        import pyarrow as pa

        # The private anonymous file is the exact copy authenticated above. Subsequent
        # changes to the durable pathname cannot change the batches sent to COPY.
        with TemporaryFile(dir=self.path.parent) as owned:
            self._copy(owned, check_active=check_active)
            owned.seek(0)
            with pa.ipc.open_stream(owned) as reader:
                yield reader


@dataclass(frozen=True)
class CompletionDraft:
    identity: str
    release_id: str
    operation: str
    basis: bytes
    request: bytes
    population_upload: PopulationUploadFile | None = None

    def native_request(self) -> WireRetainDataCompletionIntentRequest:
        """Return the exact original native intake request under its captured fence."""
        return cast("WireRetainDataCompletionIntentRequest", native_json_loads(self.request))


@dataclass(frozen=True)
class DraftRetirement:
    draft_id: str
    state: Literal["retired", "retained", "unavailable"]
    reason: str
    intent_id: str | None = None
    receipt_id: str | None = None
    failure_id: str | None = None


def completion_draft_store(
    root: Path,
    target: StorageTarget,
    max_bytes: int,
    *,
    writer_schema_for_release: Callable[[str], bytes] | None = None,
) -> CompletionDraftStore:
    namespace = sha256(
        json_bytes(
            {"system_identifier": target.system_identifier, "database_oid": target.database_oid}
        )
    ).hexdigest()
    return CompletionDraftStore(
        root / namespace, max_bytes=max_bytes, writer_schema_for_release=writer_schema_for_release
    )


def captured_writer_schema(connection, release_id: str) -> bytes:
    """Resolve the original writer through its authenticated release dependencies."""
    from .data_operation_wire import wire_contracts
    from .releases import load_release_inputs

    _, dependencies, _, _ = load_release_inputs(connection, release_id)
    return json_bytes(
        wire_contracts(dependencies.artifacts)["retain_data_completion_intent"]["input"]
    )


def _candidate_key(request_id: str, generation: int) -> str:
    return sha256(json_bytes({"request_id": request_id, "generation": generation})).hexdigest()


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


class DraftWriterContractUnavailable(ValueError):
    """Retained bytes lack an available authenticated writer interpretation."""


class CompletionDraftStore:
    """One private local owner with independently durable content and acknowledgment."""

    def __init__(
        self,
        root: Path,
        *,
        max_bytes: int,
        writer_schema_for_release: Callable[[str], bytes] | None = None,
    ):
        if type(max_bytes) is not int or max_bytes < 1:
            raise ValueError("completion draft requires a positive byte bound")
        self.root = root
        self.max_bytes = max_bytes
        self.writer_schema_for_release = writer_schema_for_release
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = root.stat()
        if root.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("completion draft root has foreign file custody")
        _sync_directory(root.parent)
        with self._owner():
            self._recover_unacknowledged()

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

    def _recover_unacknowledged(self) -> None:
        """Recover abandoned local staging while holding the draft owner lock."""
        changed = False
        for path in self.root.glob("pending-*"):
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                    raise ValueError("completion staging has foreign file custody")
                path.unlink()
                changed = True
            finally:
                os.close(descriptor)
        for path in self.root.iterdir():
            matched = re.fullmatch(r"(?:[0-9a-f]{64}\.)?([0-9a-f]{64})\.(body|arrow|candidate)", path.name)
            if matched is None:
                continue
            identity = matched[1]
            if not any((self.root / (identity + suffix)).exists() for suffix in (".ack", ".retired")):
                path.unlink()
                changed = True
        if changed:
            _sync_directory(self.root)

    def _atomic(self, name: str, content: bytes) -> None:
        temporary = self.root / ("pending-" + uuid4().hex)
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as sink:
                fcntl.flock(fd, fcntl.LOCK_EX)
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
        writer_schema: bytes,
        population_upload_batches: Iterable[pa.RecordBatch] | None = None,
        population_upload_profile: ArrowWriteProfile | None = None,
        max_population_upload_bytes: int | None = None,
    ) -> CompletionDraft:
        """Persist the original complete request before acknowledging it to its caller."""
        if not release_id or operation not in SUPPORTED_OPERATIONS:
            raise ValueError(
                "completion draft requires its original release and supported operation"
            )
        if (population_upload_batches is None) != (population_upload_profile is None):
            raise ValueError("completion upload requires both its batches and write profile")
        validate_wire_schema(writer_schema, request)
        content = json_bytes(dict(request))
        if len(content) > self.max_bytes or len(basis) > self.max_bytes:
            raise ValueError("completion draft exceeds its byte bound")
        # Canonical bytes retain every supplied producing determinant without narrowing it.
        basis = json_bytes(native_json_loads(basis))
        metadata = dict(
            format="ddo-completion-draft-v2",
            writer_schema=writer_schema.hex(),
            writer_schema_sha256=sha256(writer_schema).hexdigest(),
            release_id=release_id,
            operation=operation,
            basis=native_json_loads(basis),
            request_sha256=sha256(content).hexdigest(),
            request_bytes=len(content),
        )
        temporary = self.root / ("pending-" + uuid4().hex)
        staging_owner = None
        try:
            if population_upload_batches is not None:
                from .population_transfer import write_population_upload

                assert population_upload_profile is not None
                maximum = self.max_bytes - len(content)
                if max_population_upload_bytes is not None:
                    maximum = min(maximum, max_population_upload_bytes)
                with self._owner():
                    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    fcntl.flock(descriptor, fcntl.LOCK_EX)
                    staging_owner = os.dup(descriptor)
                with os.fdopen(descriptor, "wb") as stream:
                    size, digest = write_population_upload(
                        population_upload_profile,
                        population_upload_batches,
                        stream,
                        max_bytes=maximum,
                        check_active=check_active,
                    )
                    stream.flush()
                    os.fsync(stream.fileno())
                metadata.update(
                    format="ddo-completion-draft-v3", upload_bytes=size, upload_sha256=digest
                )
            envelope = json_bytes(metadata)
            if len(envelope) > self.max_bytes:
                raise ValueError("completion draft envelope exceeds its byte bound")
            identity = sha256(envelope).hexdigest()
            with self._owner():
                check_active()
                if (self.root / (identity + ".retired")).exists():
                    raise ValueError("completion draft is already retired")
                if (self.root / (identity + ".ack")).exists():
                    return self._open(identity)
                try:
                    self._atomic(identity + ".body", content)
                    if population_upload_batches is not None:
                        temporary.replace(self.root / (identity + ".arrow"))
                        _sync_directory(self.root)
                    lookup = _candidate_key(request["request_id"], request["generation"])
                    self._atomic(lookup + "." + identity + ".candidate", b"")
                    check_active()
                    self._atomic(identity + ".ack", envelope)
                    return self._open(identity, check_active=check_active)
                except BaseException:
                    if not (self.root / (identity + ".ack")).exists():
                        for suffix in (".body", ".arrow"):
                            (self.root / (identity + suffix)).unlink(missing_ok=True)
                        for path in self.root.glob("*." + identity + ".candidate"):
                            path.unlink()
                        _sync_directory(self.root)
                    raise

        finally:
            temporary.unlink(missing_ok=True)
            if staging_owner is not None:
                os.close(staging_owner)

    def _open(self, identity: str, *, check_active=lambda: None) -> CompletionDraft:
        identity = _identity(identity)
        envelope = _read(self.root / (identity + ".ack"), max_bytes=self.max_bytes)
        if sha256(envelope).hexdigest() != identity:
            raise ValueError("completion acknowledgment differs from its content identity")
        value = native_json_loads(envelope)
        common = {"format", "release_id", "operation", "basis", "request_sha256", "request_bytes"}
        format_ = value.get("format")
        writer = common | {"writer_schema", "writer_schema_sha256"}
        has_population = format_ == "ddo-completion-draft-v3"
        if (format_ == "ddo-completion-draft-v2" and set(value) == writer) or (
            has_population and set(value) == writer | {"upload_bytes", "upload_sha256"}
        ):
            writer_schema = bytes.fromhex(value["writer_schema"])
            if sha256(writer_schema).hexdigest() != value["writer_schema_sha256"]:
                raise ValueError(
                    "completion draft writer schema differs from its acknowledged digest"
                )
        elif value.get("format") == "ddo-completion-draft-v1" and set(value) == common:
            if self.writer_schema_for_release is None:
                raise DraftWriterContractUnavailable(
                    "retained completion writer contract is unavailable"
                )
            try:
                writer_schema = self.writer_schema_for_release(value["release_id"])
            except KeyError as error:
                if error.args != (value["release_id"],):
                    raise
                raise DraftWriterContractUnavailable(
                    "retained completion writer release is unavailable"
                ) from error
            except (ValueError, FileNotFoundError) as error:
                raise DraftWriterContractUnavailable(
                    "retained completion writer contract cannot be acquired"
                ) from error
        else:
            raise ValueError("unsupported private completion draft")
        request = _read(
            self.root / (identity + ".body"),
            max_bytes=self.max_bytes,
            expected_bytes=value["request_bytes"],
        )
        if sha256(request).hexdigest() != value["request_sha256"]:
            raise ValueError("completion draft differs from its acknowledged body")
        validate_wire_schema(writer_schema, native_json_loads(request))
        upload = None
        if has_population:
            if type(value["upload_bytes"]) is not int or not 0 < value[
                "upload_bytes"
            ] <= self.max_bytes - len(request):
                raise ValueError("completion population upload exceeds its acknowledged byte bound")
            upload = PopulationUploadFile(
                self.root / (identity + ".arrow"), value["upload_bytes"], value["upload_sha256"]
            )
            upload._copy(check_active=check_active)
        return CompletionDraft(
            identity,
            value["release_id"],
            value["operation"],
            json_bytes(value["basis"]),
            request,
            upload,
        )

    def open(self, identity: str) -> CompletionDraft:
        with self._owner():
            return self._open(identity)

    def candidates(self, request_id: str, generation: int) -> Iterator[CompletionDraft]:
        """Read acknowledged original candidates before native applicability checks."""
        lookup = _candidate_key(request_id, generation)
        with self._owner():
            candidates = tuple(sorted(self.root.glob(lookup + ".*.candidate")))
        for path in candidates:
            with self._owner():
                identity = _identity(path.name.split(".")[1])
                if (self.root / (identity + ".retired")).exists() or not (
                    self.root / (identity + ".ack")
                ).exists():
                    continue
                try:
                    draft = self._open(identity)
                except DraftWriterContractUnavailable:
                    import logging

                    logging.getLogger(__name__).warning(
                        "Retained draft %s needs regeneration because its writer contract is unavailable",
                        identity,
                    )
                    continue
                original = draft.native_request()
                if (original["request_id"], original["generation"]) != (request_id, generation):
                    raise ValueError("completion candidate differs from the selected request")
            yield draft

    def retire(
        self,
        identity: str,
        *,
        project_id: str,
        inspect: Callable[
            [WireInspectDataCompletionDraftRequest], WireInspectDataCompletionDraftResult
        ],
        confirmed_publication: tuple[CompletionDraft, str] | None = None,
    ) -> DraftRetirement:
        """Delete acknowledged private bytes after exact settled native custody."""
        identity = _identity(identity)
        if not project_id:
            raise ValueError("completion draft retirement requires an exact project")
        marker_name = identity + ".retired"
        with self._owner():
            try:
                marker = finite_json_loads(_read(self.root / marker_name, max_bytes=self.max_bytes))
            except FileNotFoundError:
                try:
                    draft = self._open(identity)
                except DraftWriterContractUnavailable:
                    return DraftRetirement(identity, "retained", "writer-contract-unavailable")
                except FileNotFoundError:
                    standing = (
                        "retained" if (self.root / (identity + ".body")).exists() else "unavailable"
                    )
                    return DraftRetirement(identity, standing, "no-complete-acknowledgment")
                original = draft.native_request()
                origin = native_json_loads(draft.basis).get("execution_origin")
                if not isinstance(origin, str) or not origin:
                    return DraftRetirement(identity, "retained", "unattributed")
                result = inspect(
                    {
                        "project_id": project_id,
                        "origin_id": origin,
                        "draft_id": identity,
                        "producer": original,
                    }
                )
                confirmed = (
                    result["reason"] == "retirement-unconfirmed"
                    and confirmed_publication is not None
                    and confirmed_publication == (draft, result["intent_id"])
                )
                if result["state"] != "eligible" and not confirmed:
                    return DraftRetirement(
                        identity,
                        "retained",
                        result["reason"],
                        result["intent_id"],
                        result["receipt_id"],
                        result["failure_id"],
                    )
                marker = dict(
                    format="ddo-completion-draft-retirement-v1",
                    draft_id=identity,
                    project_id=project_id,
                    origin_id=origin,
                    lookup=_candidate_key(original["request_id"], original["generation"]),
                    intent_id=result["intent_id"],
                    receipt_id=result["receipt_id"],
                    failure_id=result["failure_id"],
                    retirement="owner-confirmed" if confirmed else "failed-attempt",
                )
                self._retirement_paths(marker, identity, project_id)
                self._atomic(marker_name, json_bytes(marker))
            for path in self._retirement_paths(marker, identity, project_id):
                path.unlink(missing_ok=True)
            _sync_directory(self.root)
            return DraftRetirement(
                identity,
                "retired",
                "native-publication-and-retirement",
                marker["intent_id"],
                marker["receipt_id"],
                marker["failure_id"],
            )

    def _retirement_paths(self, marker, identity, project_id):
        if (
            marker["format"] != "ddo-completion-draft-retirement-v1"
            or marker["draft_id"] != identity
            or marker["project_id"] != project_id
            or not all(
                isinstance(marker[key], str) and marker[key]
                for key in ("origin_id", "intent_id", "receipt_id")
            )
            or (
                (marker["retirement"] != "owner-confirmed" or marker["failure_id"] is not None)
                and (
                    marker["retirement"] != "failed-attempt"
                    or not isinstance(marker["failure_id"], str)
                    or not marker["failure_id"]
                )
            )
        ):
            raise ValueError("completion retirement marker differs from its selected custody")
        lookup = _identity(marker["lookup"])
        paths = tuple(
            self.root / name
            for name in (
                lookup + "." + identity + ".candidate",
                identity + ".ack",
                identity + ".body",
                identity + ".arrow",
            )
        )
        for path in paths:
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise ValueError("completion retirement path has foreign file custody")
        return paths
