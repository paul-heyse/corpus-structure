"""Attempt-fenced durable replay journal for one private PDF build.

A journal acknowledges producer files, never database publication. Previous-attempt
files remain inert until recovery proves that producer's physical retirement.
Spools, including rasters/assemblies, remain after sealing for explicit authenticated
cleanup; this journal never silently collects producer evidence.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from .pdf_stream_types import PdfReplayRef


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
        self.root = root / build_id / f"attempt-{attempt}-{sha256(holder.encode()).hexdigest()[:16]}"
        self.root.mkdir(parents=True, exist_ok=False, mode=0o700)
        self.path = self.root / "manifest.jsonl"
        self._entries: dict[str, PdfReplayRef] = {}
        self._write({"version": "pdf-build-spool-1", "build_id": build_id,
                     "task_id": task_id, "attempt": attempt, "holder": holder}, mode="x")
        for directory in (self.root.parent, root):
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def _write(self, value: dict[str, Any], *, mode: str = "a") -> None:
        self.check_active()
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
        value = asdict(replay)
        value["path"] = key
        self._write({"replay": value})
        self._entries[key] = replay

    @property
    def entries(self) -> tuple[PdfReplayRef, ...]:
        return tuple(self._entries.values())

    def report(self) -> dict[str, Any]:
        self.check_active()
        return {"manifest_sha256": sha256(self.path.read_bytes()).hexdigest(),
                "artifacts": [{"digest": replay.digest, "byte_length": replay.byte_length,
                               "family": replay.family, "page_no": replay.page_no}
                              for replay in self.entries]}
