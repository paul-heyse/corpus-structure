"""Formatting and output custody shared by current model projections."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY = PACKAGE.parents[3]

CURRENT_OUTPUTS = (
    "semantic/_source_admission_calls.py",
    "semantic/_typed_columns.py",
    "semantic/identifiers.py",
    "semantic/_data_operation_fates.py",
    "semantic/_pdf_native_calls.py",
    "semantic/_pdf_native_ids.py",
    "semantic/_data_operation_wire.py",
)


def _format(path: str, text: str) -> str:
    """Render Python with the repository's selected Ruff options."""
    for args in (["check", "--fix", "--quiet", "--exit-zero"], ["format"]):
        done = subprocess.run(
            [sys.executable, "-m", "ruff", *args, "--stdin-filename", path, "-"],
            input=text,
            capture_output=True,
            text=True,
            cwd=REPOSITORY,
            check=False,
        )
        if done.returncode != 0:
            raise RuntimeError(f"ruff {args[0]} failed on {path}: {done.stderr}")
        text = done.stdout
    return text


def compilers() -> dict[str, str]:
    """Current released-model projection toolchain recorded in managed previews."""
    return {
        "linkml-runtime": importlib.metadata.version("linkml-runtime"),
        "linkml": importlib.metadata.version("linkml"),
        "corpus_structure.model.compiled": "1",
    }
