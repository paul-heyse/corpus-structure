"""Captured-source, wire and CPU construction support for DDO ports."""

from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.semantic.cpu_execution import CPUExecutionScope
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.identity import claim_source_item__data_operation__
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from corpus_structure.semantic.types import PreparedRelease, SourceArtifact


def kind(model, role):
    name = next(r.kind for r in model.operations[0].roles if r.name == role)
    return next(i.key for i in model.identities if i.owner == name and i.domain == "kind")


def fixture_source(
    tmp_path,
    monkeypatch,
    signature="index: int = 2",
    body="return str(index)",
    *,
    metadata=None,
    header="",
    returns="str",
    profiles=(),
):
    declaration = copy.deepcopy(metadata or claim_source_item__data_operation__)
    name = "ddo_port_" + tmp_path.name.replace("-", "_")
    source = (
        f"{header}\ndef derive({signature}) -> {returns}:\n    {body}\n"
        f"derive__data_operation__ = {declaration!r}\n"
    )
    path = tmp_path / (name + ".py")
    path.write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    inputs = PythonSourceCollection(
        (PythonSource(name, source.encode(), str(path)),), generated_interfaces=profiles
    )
    return compile_data_operations(python_sources=inputs), inputs


def scope():
    return CPUExecutionScope(
        cast(PreparedRelease, SimpleNamespace(release_id="test:no-schema-capsule")),
        CharacterizationExecutionPolicy(workers=1, max_submissions=1),
        retain_schema=False,
    )


def captured(content: bytes | None = None):
    source = (
        Path(__file__).parents[2] / "src/corpus_structure/model/semantic/data-operation-native.yaml"
    )
    from corpus_structure.semantic.data_operation_execution_evidence import (
        SOURCE,
        execution_evidence_schema,
    )
    from corpus_structure.semantic.data_operation_support import (
        ORIGINAL_REFERENCE_SCHEMA,
        ORIGINAL_SUPPORT_REFERENCE_SCHEMA,
        original_source_reference_schema,
        original_support_reference_schema,
    )

    return (
        SourceArtifact(
            "native/data-operation-protocol.yaml",
            source.read_bytes() if content is None else content,
        ),
        SourceArtifact(SOURCE, execution_evidence_schema()),
        SourceArtifact(ORIGINAL_REFERENCE_SCHEMA, original_source_reference_schema()),
        SourceArtifact(ORIGINAL_SUPPORT_REFERENCE_SCHEMA, original_support_reference_schema()),
    )
