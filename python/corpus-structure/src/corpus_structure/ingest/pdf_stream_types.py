"""Owned file capabilities crossing finite PDF worker boundaries; never native handles."""

from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass
from hashlib import file_digest, sha256
from pathlib import Path
from tempfile import mkdtemp


@dataclass(frozen=True, slots=True)
class PdfSourceRef:
    path: Path
    digest: str
    byte_length: int
    device: int
    inode: int
    mtime_ns: int

    def verify(self) -> None:
        info = self.path.lstat()
        if not stat.S_ISREG(info.st_mode) or (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
        ) != (self.device, self.inode, self.byte_length, self.mtime_ns):
            raise ValueError("owned PDF source was replaced or changed")
        if info.st_mode & 0o222:
            raise ValueError("owned PDF source is writable")


class OwnedPdfSource:
    """Copy and hash once into exclusive read-only custody, retained until owner close."""

    def __init__(self, reference: PdfSourceRef, root: Path):
        self.reference, self.root = reference, root

    @classmethod
    def acquire(
        cls, path: Path, root: Path, *, expected_digest: str | None = None
    ) -> OwnedPdfSource:
        root.mkdir(parents=True, exist_ok=True)
        directory = Path(mkdtemp(prefix="pdf-source-", dir=root))
        os.chmod(directory, 0o700)
        target = directory / "original.pdf"
        try:
            with path.open("rb") as source, target.open("xb") as sink:
                header = source.read(1024)
                if b"%PDF-" not in header:
                    raise ValueError("source is not a PDF")
                digest_builder = sha256(header)
                sink.write(header)
                while chunk := source.read(65536):
                    digest_builder.update(chunk)
                    sink.write(chunk)
                sink.flush()
                os.fsync(sink.fileno())
            digest = digest_builder.hexdigest()
            if expected_digest is not None and digest != expected_digest:
                raise ValueError("source digest differs from admitted original")
            target.chmod(0o400)
            info = target.stat()
            return cls(
                PdfSourceRef(
                    target, digest, info.st_size, info.st_dev, info.st_ino, info.st_mtime_ns
                ),
                directory,
            )
        except BaseException:
            shutil.rmtree(directory)
            raise

    def close(self) -> None:
        # The owner explicitly ends all reader/replay obligations before this call.
        if self.root.exists():
            self.reference.verify()
            shutil.rmtree(self.root)

    def __enter__(self) -> PdfSourceRef:
        self.reference.verify()
        return self.reference

    def __exit__(self, *exc: object) -> None:
        self.close()


@dataclass(frozen=True, slots=True)
class PdfReplayRef:
    path: Path
    digest: str
    byte_length: int
    family: str
    rows: int = 0

    def verify(self) -> None:
        if self.path.stat().st_size != self.byte_length:
            raise ValueError("PDF replay size changed")
        with self.path.open("rb") as source:
            if file_digest(source, "sha256").hexdigest() != self.digest:
                raise ValueError("PDF replay bytes changed")


@dataclass(frozen=True, slots=True)
class PdfStreamRequest:
    source: PdfSourceRef
    spool_root: Path
    record_root: Path
    build_id: str
    release_id: str
    page_range: tuple[int, int] | None = None
    observation_replay: PdfReplayRef | None = None
    structural_pin: dict | None = None
    integration_policy: dict | None = None
    reconciliation_root: Path | None = None


@dataclass(frozen=True, slots=True)
class PdfReplayReady:
    replay: PdfReplayRef


@dataclass(frozen=True, slots=True)
class PdfStreamReply:
    conversion_status: str
    errors: tuple[str, ...]
    recipe: bytes
    page_replays: tuple[PdfReplayRef, ...]
    record_replays: tuple[PdfReplayRef, ...]
