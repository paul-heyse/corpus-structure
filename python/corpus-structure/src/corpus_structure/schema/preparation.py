"""Checkout paths and serialization for reviewed model writers."""

from __future__ import annotations

import fcntl
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

PACKAGE_PATH = Path("python/corpus-structure/src/corpus_structure")
MODEL_PATH = PACKAGE_PATH / "model"


@contextmanager
def writer_lock(root: Path) -> Generator[None]:
    """Serialize the supported model writers in this checkout."""
    lock_path = root / "build/ci/.model-writer.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield
