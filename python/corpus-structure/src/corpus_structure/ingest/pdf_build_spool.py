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
from collections.abc import Callable
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .pdf_stream_types import PdfReplayRef


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
        for name in ("request_id", "release_id", "operation", "definition", "recipe",
                     "implementation", "execution_profile", "runtime_id"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError("PDF producer basis has no exact " + name)
        if type(self.generation) is not int or self.generation < 1:
            raise ValueError("PDF producer basis has no request generation")
        for digest in (self.runtime_manifest_digest, self.pdf_domain_digest):
            if re.fullmatch("[0-9a-f]{64}", digest) is None:
                raise ValueError("PDF producer basis requires exact native/runtime digests")

    def determining_basis(self):
        # Runtime IDs/manifests remain each contributor's actual provenance.
        # The admitted execution profile and implementation establish reuse fit.
        return (self.request_id, self.generation, self.release_id, self.operation,
                self.definition, self.recipe, self.implementation, self.execution_profile,
                self.pdf_domain_digest)


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

    def reusable_with(self, other: PdfSpoolPremises) -> bool:
        return self.producer.determining_basis() == other.producer.determining_basis() and (
            self.source_digest, self.native_recipe_digest, self.native_schema_digest,
            self.payload_schema_digest, self.asset_manifest_digest, self.packages, self.page_range,
        ) == (
            other.source_digest, other.native_recipe_digest, other.native_schema_digest,
            other.payload_schema_digest, other.asset_manifest_digest, other.packages, other.page_range,
        )


class PdfSpoolWriterLease:
    """A shared open-file-description survives until every actual writer dies.

    Close descriptors; never LOCK_UN, which would unlock every duplicate. A
    child deliberately leaves its raw descriptor open until OS process death,
    covering Docling model threads abandoned after a bounded stage timeout.
    """

    def __init__(self, path: Path):
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
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
        try:
            self._write({"version": "pdf-build-spool-1", "build_id": build_id,
                         "task_id": task_id, "attempt": attempt, "holder": holder,
                         "writer": self.writer_lease.identity}, mode="x")
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

    @property
    def entries(self) -> tuple[PdfReplayRef, ...]:
        return tuple(self._entries.values())

    def report(self) -> dict[str, Any]:
        self.check_active()
        return {
            "manifest_sha256": sha256(self.path.read_bytes()).hexdigest(),
            "artifacts": [
                {
                    "digest": replay.digest,
                    "byte_length": replay.byte_length,
                    "family": replay.family,
                    **({"page_no": replay.page_no} if replay.page_no is not None else {}),
                }
                for replay in self.entries
            ],
        }
