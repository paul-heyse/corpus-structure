"""Formatting and output custody shared by current model projections."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy import MetaData

    from corpus_structure.semantic.pdf_domain import PdfDomainContract
    from corpus_structure.semantic.types import SourceArtifact


PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY = PACKAGE.parents[3]


@dataclass(frozen=True)
class _FacadeInputs:
    metadata: MetaData
    pdf_domain: PdfDomainContract
    native_sources: tuple[SourceArtifact, ...]


@dataclass(frozen=True)
class _FacadeOutput:
    path: str
    render: Callable[[_FacadeInputs], str]


def _facade_outputs() -> tuple[_FacadeOutput, ...]:
    from corpus_structure.semantic import pdf_call_generation, typed_generation
    from corpus_structure.semantic.data_operation_wire import generated_wire_source
    from corpus_structure.semantic.original_document_contracts import generated_source_calls

    def data_wire(inputs: _FacadeInputs) -> str:
        return _format(
            "semantic/_data_operation_wire.py", generated_wire_source(inputs.native_sources)
        )

    return (
        _FacadeOutput(
            "semantic/_source_admission_calls.py",
            lambda inputs: generated_source_calls(target_metadata=inputs.metadata),
        ),
        _FacadeOutput(
            "semantic/_typed_columns.py",
            lambda inputs: typed_generation.generated_source(inputs.metadata),
        ),
        _FacadeOutput(
            "semantic/identifiers.py",
            lambda inputs: typed_generation.generated_identifiers(inputs.metadata),
        ),
        _FacadeOutput(
            "semantic/_data_operation_fates.py",
            lambda inputs: typed_generation.generated_fates(
                inputs.metadata.info["physical_sources"]["data-operation-native.yaml"]
            ),
        ),
        _FacadeOutput(
            "semantic/_pdf_native_calls.py",
            lambda inputs: pdf_call_generation.generated_source(
                target_metadata=inputs.metadata, domain=inputs.pdf_domain
            ),
        ),
        _FacadeOutput(
            "semantic/_pdf_native_ids.py",
            lambda inputs: pdf_call_generation.generated_enums(domain=inputs.pdf_domain),
        ),
        _FacadeOutput("semantic/_data_operation_wire.py", data_wire),
    )


def native_facade_paths() -> frozenset[str]:
    """Identify generated paths relative to the package's authored source root."""
    return frozenset(output.path for output in _facade_outputs())


def native_facades(target: MetaData, logical: dict[str, bytes]) -> dict[str, str]:
    """Render the declared facade outputs from the same held native inputs."""
    from corpus_structure.semantic.pdf_domain import PdfDomainContract
    from corpus_structure.semantic.target_installation import capture_target_installation

    captured = capture_target_installation(target, logical_sources=logical)
    pdf, *sources = captured.pdf_sources
    inputs = _FacadeInputs(
        target,
        PdfDomainContract(pdf.content, tuple(sources)),
        captured.authoring_inputs.native_sources,
    )
    package = PACKAGE.relative_to(REPOSITORY)
    return {
        (package / output.path).as_posix(): output.render(inputs) for output in _facade_outputs()
    }


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
