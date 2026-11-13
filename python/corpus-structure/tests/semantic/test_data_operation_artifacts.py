"""Derived products retain model/encoding/call identities and the shared emitter."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, replace
from hashlib import sha256

import pytest

from corpus_structure.semantic.contracts import OperationCallBinding, OperationFieldBinding, OperationFieldType
from corpus_structure.semantic.data_operation_artifacts import compile_data_operation_artifacts
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
from corpus_structure.semantic.identity import canonical_bytes, claim_source_item__data_operation__
from corpus_structure.semantic.operation_call_generation import render_call_bindings
from corpus_structure.semantic.types import SourceArtifact


def inputs():
    metadata = copy.deepcopy(claim_source_item__data_operation__)
    metadata["id"] = "data.read_demand_result"
    metadata["profile"] = "read"
    metadata["roles"][0].update(name="request", parameter="payload", kind="json")
    metadata["roles"][1].update(name="result", parameter="payload", kind="json")
    metadata["binding"]["roles"] = ["request"]
    model = compile_data_operations(declarations=(SourceArtifact("native-operations.json", canonical_bytes({"version": MODEL_VERSION, "operations": [metadata]})),))
    field = OperationFieldBinding("payload", "native:data.read_demand_result.payload", False, native_parameter="p_payload", resolved=OperationFieldType("json_payload", False, False))
    call = OperationCallBinding("read_demand_result", "ops.read_demand_result", (field,), result_class="ReadDemandResult", result_fields=(field,), cardinality="one", ordered=False, source_digest="fixed-native-source", result_mode="json")
    return model, (("data.read_demand_result", call),)


def test_artifact_manifest_carries_complete_correspondence_and_emission_identities():
    model, calls = inputs()
    artifact = compile_data_operation_artifacts(model, calls, native_source_digest="trusted-native")
    manifest = json.loads(artifact.manifest)
    assert manifest["model_digest"] == sha256(model.content).hexdigest()
    assert manifest["encoding"] == "1"
    assert manifest["native_source_digest"] == "trusted-native"
    assert manifest["calls_digest"] == sha256(artifact.calls).hexdigest()
    assert manifest["identifiers_digest"] == sha256(artifact.identifiers).hexdigest()
    assert manifest["calls"][0][0] == "data.read_demand_result"
    expected = replace(calls[0][1], requires_context=True)
    assert manifest["calls"][0][1] == json.loads(canonical_bytes(asdict(expected)))
    assert b".data_operation_admission import require_data_operation_call_context" in artifact.calls
    assert b"projection_context: PreparedRelease," in artifact.calls
    assert b"DataOperationWireValue as OperationResult" in artifact.calls
    assert b"model_validate_json(value, strict=True)" in artifact.calls
    assert b"func.ops.read_demand_result" in artifact.calls
    assert b"bound_execution_model" not in artifact.calls
    assert tuple(name for name, _ in artifact.files) == ("data_operation_ports.json", "data_operation_calls.py", "data_operation_ids.py")
    compile(artifact.calls, "archived_data_operation_calls.py", "exec")


def test_neutral_renderer_is_the_same_native_result_and_core_call_mechanism():
    _, calls = inputs()
    source = render_call_bindings(calls)
    digest = sha256(canonical_bytes([asdict(calls[0][1])])).hexdigest()
    assert digest in source
    assert "_read_demand_result_statement = select(" in source
    assert "native_result_scope(" in source
    assert "ReadDemandResult.model_validate_json(value, strict=True)" in source


def test_missing_resolved_native_source_or_duplicate_variant_refuses():
    model, calls = inputs()
    with pytest.raises(ValueError, match="source identity"):
        compile_data_operation_artifacts(model, calls, native_source_digest="")
    with pytest.raises(ValueError, match="unique"):
        compile_data_operation_artifacts(model, calls + calls, native_source_digest="trusted")
    unknown = replace(calls[0][1], source_digest=None)
    with pytest.raises(ValueError, match="closed resolved"):
        compile_data_operation_artifacts(model, ((calls[0][0], unknown),), native_source_digest="trusted")


def test_captured_generator_and_effective_role_correspondence_cannot_silently_drift():
    from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources

    model, calls = inputs()
    sources = capture_port_generator_sources()
    first = sources[0]
    changed = (replace(first, content=first.content + b"\n# changed"), *sources[1:])
    with pytest.raises(ValueError, match="differs from captured"):
        compile_data_operation_artifacts(model, calls, native_source_digest="trusted", generator_sources=changed)
    parameter = replace(calls[0][1].parameters[0], name="other")
    call = replace(calls[0][1], parameters=(parameter,))
    with pytest.raises(ValueError, match="role correspondence"):
        compile_data_operation_artifacts(model, ((calls[0][0], call),), native_source_digest="trusted", generator_sources=sources)
