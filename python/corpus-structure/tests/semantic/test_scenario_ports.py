"""Actual scenario consumers preserve domain IDs while malformed wire data stays raw."""

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def test_shared_scenario_imports_do_not_prepare_or_acquire_native_resources():
    """A fresh interpreter catches eager preparation even after a warm full collection."""
    import sys

    source = """
import importlib
import sys
sys.path[:0] = ["scripts", "python/corpus-structure/tests"]
import corpus_structure.semantic as semantic
import sqlalchemy

def unexpected(*args, **kwargs):
    raise AssertionError("scenario import prepared a release or acquired a native engine")

semantic.prepare_release = unexpected
sqlalchemy.create_engine = unexpected
for name in (
    "semantic.current_pdf_source_support",
    "evaluate.declared_record_native_support",
    "semantic.structural_native_fixture",
    "semantic.test_current_claim_owner_native",
    "semantic.test_declared_reading_resolution",
):
    importlib.import_module(name)
"""
    result = subprocess.run(
        [sys.executable, "-c", source], cwd=REPO, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
