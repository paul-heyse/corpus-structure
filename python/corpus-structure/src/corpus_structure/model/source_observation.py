"""Refreshable declaration observations, separate from executable source custody."""

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from time import time_ns

from corpus_structure.semantic.file_custody import stat_identity


@dataclass(frozen=True)
class _Observation:
    identity: tuple[int, int, int, int, int]
    content: bytes


_records: dict[Path, _Observation] = {}
_lock = RLock()


def observe_model_sources(root: Path) -> dict[str, bytes]:
    """Capture current declaration membership and reuse stable observed bytes."""
    with _lock:
        paths = tuple(sorted(p for p in root.iterdir() if p.suffix in {".yaml", ".json"}))
        result = {}
        for path in paths:
            before = stat_identity(path)
            old = _records.get(path)
            if (
                old is None
                or old.identity != before
                or time_ns() - max(before[3:]) <= 2_000_000_000
            ):
                content = path.read_bytes()
                if stat_identity(path) != before:
                    raise OSError(f"model source changed during capture: {path}")
                old = _records[path] = _Observation(before, content)
            result[path.name] = old.content
        current_paths = tuple(sorted(p for p in root.iterdir() if p.suffix in {".yaml", ".json"}))
        if current_paths != paths or any(
            stat_identity(path) != _records[path].identity for path in paths
        ):
            raise OSError("model declaration population changed during capture")
        for path in tuple(_records):
            if path.parent == root and path not in paths:
                del _records[path]
        return result
