"""Immutable runtime model composition, independently of live admission authority."""

import json
from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import read_effective_data_operations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.refusal_types import SemanticRefusal
from corpus_structure.semantic.types import PreparedArtifact, PreparedRelease
from semantic.test_data_operation_compilation import operation_source, python_inputs


def prepared_model(content, interfaces=b"opaque informational interface bytes"):
    artifact = PreparedArtifact("data_operations.json", content)
    return PreparedRelease(
        release_id="release:model-reuse",
        manifest=canonical_bytes({"data_operation_model": artifact.digest}),
        definitions=(),
        vocabularies=(),
        registry_rows=(),
        queries=(),
        artifacts=(artifact, PreparedArtifact("data_operation_source_interfaces.json", interfaces)),
        required_capabilities=(),
        diagnostics=(),
        _adapters=(),
    )


def test_bound_model_reuses_immutable_composition_without_changing_canonical_meaning():
    compiled = compile_data_operations(python_sources=python_inputs(operation_source()))
    prepared = prepared_model(compiled.content)
    first = bound_data_operation_model(prepared)
    content = first.content
    second = bound_data_operation_model(replace(prepared, release_id="release:another"))
    assert second is first
    assert second.content is content
    assert content == compiled.content == read_effective_data_operations(compiled.content).content
    assert first.identities == compiled.identities
    assert "source_interfaces" not in json.loads(content)


def test_bound_model_keys_include_both_exact_artifact_contents():
    original = compile_data_operations(python_sources=python_inputs(operation_source()))
    changed = compile_data_operations(
        python_sources=python_inputs(operation_source(body="return helper(x) + 1"))
    )
    first = bound_data_operation_model(prepared_model(original.content, b"interfaces:A"))
    new_interfaces = bound_data_operation_model(prepared_model(original.content, b"interfaces:B"))
    new_model = bound_data_operation_model(prepared_model(changed.content, b"interfaces:A"))
    assert new_interfaces is not first
    assert new_interfaces.source_interfaces == b"interfaces:B"
    assert new_interfaces.content == first.content
    assert new_model is not first
    assert new_model.content == changed.content != first.content
    without_interfaces = replace(
        prepared_model(original.content),
        artifacts=(PreparedArtifact("data_operations.json", original.content),),
    )
    assert bound_data_operation_model(without_interfaces).source_interfaces is None


def test_bound_model_cache_hit_does_not_bypass_manifest_or_artifact_refusals():
    compiled = compile_data_operations(python_sources=python_inputs(operation_source()))
    prepared = prepared_model(compiled.content)
    bound_data_operation_model(prepared)
    for manifest in (
        {},
        {"data_operation_model": "wrong"},
        {"data_operation_model": prepared.artifacts[0].digest, "execution_model_id": "old"},
    ):
        with pytest.raises(SemanticRefusal, match="unambiguous target operation model"):
            bound_data_operation_model(replace(prepared, manifest=canonical_bytes(manifest)))
    with pytest.raises(SemanticRefusal, match="unambiguous target operation model"):
        bound_data_operation_model(
            replace(prepared, artifacts=(*prepared.artifacts, prepared.artifacts[0]))
        )
    with pytest.raises(SemanticRefusal, match="ambiguous source interface"):
        bound_data_operation_model(
            replace(prepared, artifacts=(*prepared.artifacts, prepared.artifacts[1]))
        )
    historical = json.loads(compiled.content)
    historical["version"] = "unsupported"
    with pytest.raises(ValueError, match="unsupported data-operation model version"):
        bound_data_operation_model(prepared_model(canonical_bytes(historical)))
