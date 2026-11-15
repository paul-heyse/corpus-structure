"""Captured-source, wire and CPU construction support for DDO ports."""

from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.semantic.cpu_execution import CPUExecutionScope
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from semantic.data_operation_declaration_support import contract
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from corpus_structure.semantic.types import PreparedRelease, SourceArtifact


def kind(model, role):
    name = next(r.kind for r in model.operations[0].roles if r.name == role)
    return next(i.key for i in model.identities if i.owner == name and i.domain == "kind")


def controlled_port_declaration():
    value = contract(
        implementation_coverage=True,
        id="urn:controlled:port-index-address",
        subject="document",
        subject_definition={"id": "document", "identifier_kind": "string", "scope": "project"},
        context=["controlled-index-address"],
        behavior="controlled-original-callable-v1",
        applicability=[], invariants=[],
        outcomes=["addressed", "invalid-index"],
        state_dimensions=[{"name": "completion", "values": ["pending", "success", "failed"]}],
        transitions=[
            {"dimension": "completion", "before": "pending", "after": "success", "outcome": "addressed"},
            {"dimension": "completion", "before": "pending", "after": "failed", "outcome": "invalid-index"},
        ],
        binding={"operator": "scan", "roles": ["index"]},
    )
    value["roles"][0].update(name="index", parameter="index")
    value["roles"][0]["support"]["coverage"]["role"] = "index"
    value["roles"][1].update(name="address", kind="string")
    return value


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
    declaration = copy.deepcopy(metadata if metadata is not None else controlled_port_declaration())
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

    from corpus_structure.semantic.data_operation_visual_read import SOURCE as VISUAL_SOURCE, visual_read_schema

    return (
        SourceArtifact(
            "native/data-operation-protocol.yaml",
            source.read_bytes() if content is None else content,
        ),
        SourceArtifact(SOURCE, execution_evidence_schema()),
        SourceArtifact(ORIGINAL_REFERENCE_SCHEMA, original_source_reference_schema()),
        SourceArtifact(ORIGINAL_SUPPORT_REFERENCE_SCHEMA, original_support_reference_schema()),
        SourceArtifact(VISUAL_SOURCE, visual_read_schema()),
    )
