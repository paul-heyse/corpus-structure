"""The compiled statistics version, once per session, for the `validate` tests (P0-S-2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus_structure.schema.compile import CompiledSchema, compile_paths

REPO = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="session")
def stats() -> CompiledSchema:
    return compile_paths([REPO / "domains/statistics"])
