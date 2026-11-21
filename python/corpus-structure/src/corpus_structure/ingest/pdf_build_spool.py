"""Attempt-fenced durable replay journal for one private PDF build.

A journal acknowledges producer files, never database publication. Previous-attempt
files remain inert until recovery proves that producer's physical retirement.
Spools, including rasters/assemblies, remain after sealing for explicit authenticated
cleanup; this journal never silently collects producer evidence.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import stat
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, fields, replace
from hashlib import sha256
from pathlib import Path
from typing import Any

from corpus_structure.core.work import PhysicalRetirementUncertain

from .pdf_stream_types import PdfPageRecovery, PdfPreparedCompanionSet, PdfReplayRef, PdfStreamReply


@dataclass(frozen=True, slots=True)
class PdfSpoolProducerBasis:
    request_id: str
    generation: int
    release_id: str
    operation: str
    definition: str
    recipe: str
    implementation: str
    execution_profile: str
    runtime_id: str
    runtime_manifest_digest: str
    pdf_domain_digest: str

    def __post_init__(self):
        for name in (
            "request_id",
            "release_id",
            "operation",
            "definition",
            "recipe",
            "implementation",
            "execution_profile",
            "runtime_id",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError("PDF producer basis has no exact " + name)
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("PDF producer basis has no request generation")
        for digest in (self.runtime_manifest_digest, self.pdf_domain_digest):
            if re.fullmatch("[0-9a-f]{64}", digest) is None:
                raise ValueError("PDF producer basis requires exact native/runtime digests")


@dataclass(frozen=True, slots=True)
class PdfSpoolPremises:
    producer: PdfSpoolProducerBasis
    source_digest: str
    native_recipe_digest: str
    native_schema_digest: str
    payload_schema_digest: str
    asset_manifest_digest: str | None
    packages: tuple[tuple[str, str], ...]
    page_range: tuple[int, int] | None = None

    def __post_init__(self):
        for digest in (
            self.source_digest,
            self.native_recipe_digest,
            self.native_schema_digest,
            self.payload_schema_digest,
        ):
            if not isinstance(digest, str) or re.fullmatch("[0-9a-f]{64}", digest) is None:
                raise ValueError("PDF spool premises require exact source/recipe/schema digests")
        if (
            self.asset_manifest_digest is not None
            and re.fullmatch("[0-9a-f]{64}", self.asset_manifest_digest) is None
        ):
            raise ValueError("PDF spool premises require an exact asset manifest digest")
        if (
            not self.packages
            or any(
                len(pair) != 2 or not all(isinstance(value, str) and value for value in pair)
                for pair in self.packages
            )
            or len({pair[0] for pair in self.packages}) != len(self.packages)
        ):
            raise ValueError("PDF spool premises require unique exact package versions")
        if self.page_range is not None and (
            len(self.page_range) != 2
            or any(type(number) is not int or number < 1 for number in self.page_range)
            or self.page_range[1] < self.page_range[0]
        ):
            raise ValueError("PDF spool premises require an exact physical page selection")

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()


class PdfSpoolWriterLease:
    """A shared open-file-description survives until every actual writer dies.

    Close descriptors; never LOCK_UN, which would unlock every duplicate. A
    child deliberately leaves its raw descriptor open until OS process death,
    covering Docling model threads abandoned after a bounded stage timeout.
    """

    def __init__(self, path: Path):
        descriptor = os.open(
            path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600
        )
        self.fd: int | None = descriptor
        self.child_owned = False
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fsync(descriptor)
        except BaseException:
            os.close(descriptor)
            self.fd = None
            raise

    def __reduce__(self):
        from multiprocessing.context import get_spawning_popen
        from multiprocessing.reduction import DupFd

        if self.fd is None or get_spawning_popen() is None:
            raise ValueError("PDF writer lease may cross only owned process startup")
        return _receive_writer_lease, (DupFd(self.fd),)

    @property
    def identity(self) -> dict[str, int]:
        if self.fd is None:
            raise ValueError("PDF spool writer lease is closed")
        info = os.fstat(self.fd)
        return {"device": info.st_dev, "inode": info.st_ino}

    def close(self) -> None:
        if self.child_owned:
            raise ValueError("native writer lease is retained until OS process death")
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def _receive_writer_lease(duplicate) -> PdfSpoolWriterLease:
    lease = object.__new__(PdfSpoolWriterLease)
    lease.fd = duplicate.detach()
    lease.child_owned = True
    return lease


def canonical_native_options(options: dict) -> dict:
    """Canonicalize only pinned Docling VlmModelSpec's declared set fields."""
    result = dict(options)
    for option in (
        "picture_description_options",
        "chart_extraction_options",
        "code_formula_options",
    ):
        value = result.get(option)
        if isinstance(value, dict) and isinstance(value.get("model_spec"), dict):
            spec = dict(value["model_spec"])
            engines = spec.get("supported_engines")
            if isinstance(engines, list):
                spec["supported_engines"] = sorted(engines)
                result[option] = {**value, "model_spec": spec}
    return result


def native_preparation_identity(content: bytes) -> str:
    """Bind determining prepared mechanisms, keeping incidental resources as provenance."""
    report = json.loads(content)
    preparation = report["_preparation"]
    if preparation.get("profile") == "pdf-prepared-native-runtime-v1":
        raise ValueError(
            "PDF spool native preparation predates initialized binding custody; "
            "retain the original spool and regenerate this capture with the current producer"
        )
    if preparation.get("profile") not in {"pdf-prepared-native-runtime-v2", "pdf-prepared-native-runtime-v3"}:
        raise ValueError("PDF spool has an unsupported native preparation profile")
    determining = {
        name: preparation[name]
        for name in (
            "profile",
            "requested_options",
            "effective_options",
            "backend_options",
            "stage_scope",
            "native_variants",
            "initialized_bindings",
            "packages",
            "image_ownership",
        )
    }
    if preparation["profile"] == "pdf-prepared-native-runtime-v3":
        determining["producer_contract"] = preparation["producer_contract"]
    for name in ("requested_options", "effective_options"):
        determining[name] = canonical_native_options(
            {key: value for key, value in determining[name].items() if key != "artifacts_path"}
        )
    # Asset bytes have their own exact manifest identity. Arrow pool capacity,
    # PIDs and temporary locations do not determine a page's native meaning.
    return sha256(
        json.dumps(
            determining, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


_RECOVERY_PROOF = object()


@dataclass(frozen=True, slots=True)
class PdfSpoolOwner:
    build_id: str
    task_id: int
    attempt: int
    holder: str
    producer_id: str
    writer_device: int
    writer_inode: int


@dataclass(frozen=True, slots=True)
class VerifiedSpoolRecovery:
    """Private file capability created only under a positively acquired writer lease."""

    root: Path
    owner: PdfSpoolOwner
    premises: PdfSpoolPremises
    entries: tuple[PdfReplayRef, ...]
    manifest: bytes
    _descriptor: int | None = field(repr=False, compare=False)
    _completion: bytes | None = field(repr=False)
    _proof: object = field(repr=False, compare=False)
    manifest_digest: str = field(init=False)

    def __post_init__(self):
        if self._proof is not _RECOVERY_PROOF:
            raise ValueError("PDF recovery requires verified retired writer custody")
        object.__setattr__(self, "manifest_digest", sha256(self.manifest).hexdigest())

    def close(self):
        if self._descriptor is not None:
            os.close(self._descriptor)
            object.__setattr__(self, "_descriptor", None)

    def __enter__(self):
        return self

    def __exit__(self, *error):
        self.close()

    def __reduce__(self):
        raise ValueError("verified recovery custody stays with the native parent")

    def check_owned(self):
        if self._descriptor is None:
            raise ValueError("verified recovery custody has ended")
        info = os.fstat(self._descriptor)
        if (info.st_dev, info.st_ino) != (self.owner.writer_device, self.owner.writer_inode):
            raise ValueError("verified PDF writer identity changed")

    @property
    def preparation(self) -> PdfReplayRef | None:
        found = [entry for entry in self.entries if entry.family == "native_preparation"]
        if len(found) > 1:
            raise ValueError("PDF preparation inventory is ambiguous")
        return found[0] if found else None

    def ready_pages(self, payload_family) -> tuple[PdfPageRecovery, ...]:
        from .pdf_candidate_source import encoded_replay

        self.check_owned()
        preparation = self.preparation
        if preparation is None:
            return ()
        preparation.verify()
        identity = native_preparation_identity(preparation.path.read_bytes())
        by_family = {}
        for family in ("page", "candidate_payload", "native-raster"):
            pages = {}
            for entry in self.entries:
                if entry.family != family:
                    continue
                if entry.page_no is None or entry.page_no in pages:
                    raise ValueError("PDF recovery has an ambiguous physical page inventory")
                pages[entry.page_no] = entry
            by_family[family] = pages
        ready = []
        complete = set.intersection(*(set(pages) for pages in by_family.values()))
        for number in sorted(complete):
            page = by_family["page"][number]
            candidate = by_family["candidate_payload"][number]
            raster = by_family["native-raster"][number]
            value = json.loads(page.path.read_bytes())
            if value.get("serialization_profile") != "pydantic-native-page-envelope-v2" or (
                value["page"]["page_no"] != number
                or "confidence" not in value
                or "errors" not in value
            ):
                raise ValueError("PDF recovery page has no complete native state")
            if (
                Path(value["raster"]["path"]).resolve(),
                value["raster"]["digest"],
                value["raster"]["byte_length"],
            ) != (raster.path.resolve(), raster.digest, raster.byte_length):
                raise ValueError("PDF recovery raster differs from its page envelope")
            if encoded_replay(candidate, payload_family).page_no != number:
                raise ValueError("PDF recovery candidate differs from its physical page")
            ready.append(PdfPageRecovery(number, page, candidate, identity))
        return tuple(ready)

    def complete_reply(self) -> PdfStreamReply | None:
        self.check_owned()
        if self._completion is None:
            return None
        paths = {entry.path.relative_to(self.root).as_posix(): entry for entry in self.entries}
        completion = json.loads(self._completion)
        recipe = bytes.fromhex(completion["recipe"])
        if sha256(recipe).hexdigest() != self.premises.native_recipe_digest:
            raise ValueError("completed spool recipe differs from its premises")
        records = tuple(paths[name] for name in completion["record_paths"])
        pages = tuple(paths[name] for name in completion["page_paths"])
        if len(set(completion["record_paths"])) != len(records) or len(
            set(completion["page_paths"])
        ) != len(pages):
            raise ValueError("completed spool repeats a replay identity")
        if not records or not pages or len({page.page_no for page in pages}) != len(pages):
            raise ValueError("completed spool has no unambiguous native records/pages")
        completions = [entry for entry in self.entries if entry.family == "native_completion"]
        if len(completions) != 1:
            raise ValueError("completed spool has no exact native completion report")
        with completions[0].path.open() as source:
            native_completion = json.loads(next(source))
        if (
            native_completion.get("kind"),
            native_completion.get("status"),
            native_completion.get("source_digest"),
            native_completion.get("recipe_sha256"),
        ) != (
            "conversion",
            "success",
            self.premises.source_digest,
            self.premises.native_recipe_digest,
        ):
            raise ValueError("completed spool native completion differs from producer premises")
        if completion["conversion_status"] != "success" or self.preparation is None:
            raise ValueError("completed spool has no successful native preparation")
        sets = tuple(
            PdfPreparedCompanionSet(
                value["family"], value["replay_key"], tuple(paths[name] for name in value["paths"])
            )
            for value in completion["companion_sets"]
        )
        certificate = (
            paths[completion["certification"]] if completion["certification"] is not None else None
        )
        access = (
            paths[completion["access_replay"]] if completion["access_replay"] is not None else None
        )
        return PdfStreamReply(
            "success",
            tuple(completion["errors"]),
            recipe,
            pages,
            records,
            bytes.fromhex(completion["effective_options"]),
            sets,
            certificate,
            access,
        )


def _stored_premises(value: dict[str, Any]) -> PdfSpoolPremises:
    if set(value) != {item.name for item in fields(PdfSpoolPremises)}:
        raise ValueError("PDF spool premise fields differ from the current protocol")
    return PdfSpoolPremises(
        producer=PdfSpoolProducerBasis(**value["producer"]),
        source_digest=value["source_digest"],
        native_recipe_digest=value["native_recipe_digest"],
        native_schema_digest=value["native_schema_digest"],
        payload_schema_digest=value["payload_schema_digest"],
        asset_manifest_digest=value["asset_manifest_digest"],
        packages=tuple(tuple(pair) for pair in value["packages"]),
        page_range=tuple(value["page_range"]) if value["page_range"] is not None else None,
    )


def verify_spool_recovery(
    root: Path,
    *,
    build_id: str,
    task_id: int,
    before_attempt: int,
    check_active: Callable[[], None],
    authorize_source: Callable[[PdfSpoolOwner, PdfSpoolPremises], bool],
    source_build: tuple[str, int] | None = None,
) -> tuple[VerifiedSpoolRecovery, ...]:
    """Acquire every registered prior writer before inspecting immutable entries.

    A busy or unregistered same-build writer is a physical custody refusal. It
    never licenses concurrent fresh GPU work. No PID or expired lease inference
    and no reader for a historical manifest protocol enters this path.

    The authority must compare the entire owner (including writer inode) and
    original premises against the native candidate returned for the current
    build. Candidate IDs alone never authenticate a local manifest. Material
    compatibility is exclusively native; contribution rechecks native authority
    before any selected file is adopted.
    """
    recovered = []
    source_build_id, source_task_id = source_build or (build_id, task_id)
    if (root / source_build_id).resolve().parent != root.resolve():
        raise ValueError("PDF source build escapes its custody root")
    try:
        for directory in sorted((root / source_build_id).glob("attempt-*")):
            check_active()
            if (
                directory.is_symlink()
                or directory.resolve().parent != (root / source_build_id).resolve()
            ):
                raise ValueError("PDF attempt directory escaped build-owned custody")
            writer = directory / "WRITER"
            try:
                descriptor = os.open(writer, os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW)
            except FileNotFoundError as error:
                raise PhysicalRetirementUncertain(
                    f"unregistered PDF writer custody: {directory}"
                ) from error
            try:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as error:
                    raise PhysicalRetirementUncertain(
                        f"PDF writer still owns spool: {directory}"
                    ) from error
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                    raise ValueError("PDF writer lease has foreign file custody")
                manifest_path = directory / "manifest.jsonl"
                if manifest_path.is_symlink() or not manifest_path.is_file():
                    raise ValueError("PDF manifest has foreign file custody")
                manifest = manifest_path.read_bytes()
                lines = manifest.splitlines(keepends=True)
                # An unacknowledged partial tail is not a manifest entry.
                if lines and not lines[-1].endswith(b"\n"):
                    lines.pop()
                manifest = b"".join(lines)
                values = [json.loads(line) for line in lines]
                if not values:
                    raise ValueError("PDF spool has no durable owner header")
                header = values[0]
                if header.get("writer") != {"device": info.st_dev, "inode": info.st_ino}:
                    raise ValueError("PDF spool writer lease was replaced")
                if (
                    (header.get("version"), header.get("build_id"), header.get("task_id"))
                    != (
                        "pdf-build-spool-1",
                        source_build_id,
                        source_task_id,
                    )
                    or type(header.get("attempt")) is not int
                    or (source_build is None and header["attempt"] >= before_attempt)
                ):
                    raise ValueError("PDF spool belongs to another build or current/future attempt")
                holder = header.get("holder")
                if (
                    not isinstance(holder, str)
                    or not holder
                    or header["attempt"] < 1
                    or directory.name
                    != (f"attempt-{header['attempt']}-{sha256(holder.encode()).hexdigest()[:16]}")
                ):
                    raise ValueError("PDF spool directory differs from its exact producer fence")
                declarations = [value["premises"] for value in values[1:] if "premises" in value]
                if not declarations:
                    # Positively retired, but never qualified for recovery.
                    os.close(descriptor)
                    continue
                if (
                    len(declarations) != 1
                    or "premises" not in values[1]
                    or set(values[1]) != {"premises", "producer_id"}
                ):
                    raise ValueError("PDF spool has ambiguous producer premises")
                producer_id = values[1]["producer_id"]
                if (
                    not isinstance(producer_id, str)
                    or re.fullmatch("[0-9a-f]{64}", producer_id) is None
                ):
                    raise ValueError("PDF spool has no registered native producer identity")
                prior = _stored_premises(declarations[0])
                source_owner = PdfSpoolOwner(
                    source_build_id,
                    source_task_id,
                    header["attempt"],
                    holder,
                    producer_id,
                    info.st_dev,
                    info.st_ino,
                )
                if not authorize_source(source_owner, prior):
                    os.close(descriptor)
                    continue
                entries = []
                paths = set()
                completion = None
                for value in values[2:]:
                    if completion is not None:
                        raise ValueError("PDF spool has entries after completion")
                    if set(value) == {"replay"}:
                        fields = dict(value["replay"])
                        relative = Path(fields.pop("path"))
                        path = (directory / relative).resolve()
                        if (
                            relative.is_absolute()
                            or not path.is_relative_to(directory.resolve())
                            or path in paths
                        ):
                            raise ValueError("PDF spool has escaped or duplicate file custody")
                        replay = PdfReplayRef(path=path, **fields)
                        replay.verify()
                        paths.add(path)
                        entries.append(replay)
                    elif set(value) == {"completion"}:
                        if completion is not None:
                            raise ValueError("PDF spool has duplicate completion")
                        completion = value["completion"]
                    else:
                        raise ValueError("PDF spool has an unknown manifest entry")
                check_active()
                recovered.append(
                    VerifiedSpoolRecovery(
                        _proof=_RECOVERY_PROOF,
                        root=directory.resolve(),
                        _descriptor=descriptor,
                        owner=source_owner,
                        premises=prior,
                        entries=tuple(entries),
                        manifest=manifest,
                        _completion=None
                        if completion is None
                        else json.dumps(completion, separators=(",", ":")).encode(),
                    )
                )
            except BaseException:
                os.close(descriptor)
                raise
        return tuple(sorted(recovered, key=lambda capability: capability.owner.attempt))
    except BaseException:
        for capability in recovered:
            capability.close()
        raise


def selected_replay_bytes(root: Path, replays: tuple[PdfReplayRef, ...]) -> bytes:
    values = []
    for replay in replays:
        value = {**asdict(replay), "path": replay.path.relative_to(root).as_posix()}
        values.append(value)
    return json.dumps(values, sort_keys=True, separators=(",", ":")).encode()


def clone_recovery_entries(
    recovery: VerifiedSpoolRecovery,
    destination: PdfBuildSpool,
    entries: tuple[PdfReplayRef, ...],
    *,
    prefix: str,
) -> dict[Path, PdfReplayRef]:
    """Copy verified immutable inputs; retain original producer association separately."""
    recovery.check_owned()
    selected = set(entries)
    if not selected <= set(recovery.entries):
        raise ValueError("PDF clone names files outside verified recovery custody")
    mapped = {
        entry.path: destination.root / prefix / entry.path.relative_to(recovery.root)
        for entry in entries
    }
    copied = {}
    # Raster locations in private page envelopes follow the newly owned file.
    # Native records and candidate bytes remain byte-for-byte exact.
    for entry in sorted(entries, key=lambda entry: entry.family == "page"):
        destination.check_active()
        entry.verify()
        path = mapped[entry.path]
        path.parent.mkdir(parents=True, exist_ok=True)
        if entry.family == "page":
            value = json.loads(entry.path.read_bytes())
            old_raster = Path(value["raster"]["path"])
            if old_raster not in mapped:
                raise ValueError("recovered PDF page has no selected raster custody")
            value["raster"]["path"] = str(mapped[old_raster])
            with path.open("xb") as sink:
                sink.write(json.dumps(value, separators=(",", ":")).encode())
                sink.flush()
                os.fsync(sink.fileno())
            content = path.read_bytes()
            clone = replace(
                entry, path=path, digest=sha256(content).hexdigest(), byte_length=len(content)
            )
        else:
            with entry.path.open("rb") as source, path.open("xb") as sink:
                shutil.copyfileobj(source, sink, 1024 * 1024)
                sink.flush()
                os.fsync(sink.fileno())
            clone = replace(entry, path=path)
        destination.append(clone)
        copied[entry.path] = clone
    return copied


class PdfBuildSpool:
    def __init__(
        self,
        root: Path,
        *,
        build_id: str,
        task_id: int,
        attempt: int,
        holder: str,
        check_active: Callable[[], None],
    ) -> None:
        self.check_active = check_active
        check_active()
        root = root.resolve()
        self.root = (
            root / build_id / f"attempt-{attempt}-{sha256(holder.encode()).hexdigest()[:16]}"
        )
        self.root.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.writer_lease = PdfSpoolWriterLease(self.root / "WRITER")
        self.path = self.root / "manifest.jsonl"
        self._entries: dict[str, PdfReplayRef] = {}
        self.premises: PdfSpoolPremises | None = None
        self.producer_id: str | None = None
        self._completed = False
        try:
            self._write(
                {
                    "version": "pdf-build-spool-1",
                    "build_id": build_id,
                    "task_id": task_id,
                    "attempt": attempt,
                    "holder": holder,
                    "writer": self.writer_lease.identity,
                },
                mode="x",
            )
        except BaseException:
            self.writer_lease.close()
            raise
        for directory in (self.root.parent, root):
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def __enter__(self):
        return self

    def __exit__(self, *error):
        self.close()

    def close(self) -> None:
        self.writer_lease.close()

    def _write(self, value: dict[str, Any], *, mode: str = "a") -> None:
        self.check_active()
        _ = self.writer_lease.identity
        with self.path.open(mode, encoding="utf8") as sink:
            sink.write(json.dumps(value, separators=(",", ":"), sort_keys=True) + "\n")
            sink.flush()
            os.fsync(sink.fileno())
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        self.check_active()

    def append(self, replay: PdfReplayRef) -> None:
        self.check_active()
        if self._completed:
            raise ValueError("completed PDF spool is immutable")
        owned_path = replay.path.resolve()
        if not owned_path.is_relative_to(self.root):
            raise ValueError("PDF replay escaped attempt-owned build spool")
        replay.verify()
        # Producer files are flushed before sending their descriptor. Complete
        # custody of each rename/directory entry before making its ACK durable.
        directory = owned_path.parent
        while directory != self.root:
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            directory = directory.parent
        key = owned_path.relative_to(self.root).as_posix()
        prior = self._entries.get(key)
        if prior is not None:
            if prior != replay:
                raise ValueError("PDF spool replay identity changed")
            return
        value: dict[str, Any] = asdict(replay)
        value["path"] = key
        self._write({"replay": value})
        self._entries[key] = replay

    def declare_premises(self, premises: PdfSpoolPremises, producer_id: str) -> None:
        if self.premises is not None or self._entries:
            raise ValueError("PDF producer premises must precede every replay")
        if re.fullmatch("[0-9a-f]{64}", producer_id) is None:
            raise ValueError("PDF spool requires its registered native producer identity")
        self._write({"premises": asdict(premises), "producer_id": producer_id})
        self.premises, self.producer_id = premises, producer_id

    def complete(self, reply: PdfStreamReply) -> None:
        if self._completed or self.premises is None or reply.conversion_status != "success":
            raise ValueError("PDF completion requires exact successful producer premises")
        for family in ("native_preparation", "native_completion"):
            if sum(entry.family == family for entry in self.entries) != 1:
                raise ValueError(
                    "PDF completion requires exact native preparation/completion custody"
                )
        if sha256(reply.recipe).hexdigest() != self.premises.native_recipe_digest:
            raise ValueError("PDF completion recipe differs from producer premises")

        def paths(replays):
            values = []
            for replay in replays:
                key = replay.path.relative_to(self.root).as_posix()
                if self._entries.get(key) != replay:
                    raise ValueError("PDF completion names an unacknowledged replay")
                values.append(key)
            return values

        self._write(
            {
                "completion": {
                    "conversion_status": reply.conversion_status,
                    "errors": list(reply.errors),
                    "recipe": reply.recipe.hex(),
                    "effective_options": reply.effective_options.hex(),
                    "record_paths": paths(reply.record_replays),
                    "page_paths": paths(reply.page_replays),
                    "companion_sets": [
                        {
                            "family": value.family,
                            "replay_key": value.replay_key,
                            "paths": paths(value.replays),
                        }
                        for value in reply.companion_sets
                    ],
                    "certification": paths((reply.certification,))[0]
                    if reply.certification is not None
                    else None,
                    "access_replay": paths((reply.access_replay,))[0]
                    if reply.access_replay is not None
                    else None,
                }
            }
        )
        self._completed = True

    @property
    def entries(self) -> tuple[PdfReplayRef, ...]:
        return tuple(self._entries.values())
