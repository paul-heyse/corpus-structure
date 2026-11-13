"""Derived products retain model/encoding/call identities and the shared emitter."""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, replace
from hashlib import sha256
from typing import Any

import pytest

from corpus_structure.semantic.contracts import (
    OperationCallBinding,
    OperationFieldBinding,
    OperationFieldType,
)
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
    model = compile_data_operations(
        declarations=(
            SourceArtifact(
                "native-operations.json",
                canonical_bytes({"version": MODEL_VERSION, "operations": [metadata]}),
            ),
        )
    )
    field = OperationFieldBinding(
        "payload",
        "native:data.read_demand_result.payload",
        False,
        native_parameter="p_payload",
        resolved=OperationFieldType("json_payload", False, False),
    )
    call = OperationCallBinding(
        "read_demand_result",
        "ops.read_demand_result",
        (field,),
        result_class="ReadDemandResult",
        result_fields=(field,),
        cardinality="one",
        ordered=False,
        source_digest="trusted-native",
        result_mode="json",
    )
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
    assert tuple(name for name, _ in artifact.files) == (
        "data_operation_ports.json",
        "data_operation_calls.py",
        "data_operation_ids.py",
    )
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
        compile_data_operation_artifacts(
            model, calls + calls, native_source_digest="trusted-native"
        )
    unknown = replace(calls[0][1], source_digest=None)
    with pytest.raises(ValueError, match="closed resolved"):
        compile_data_operation_artifacts(
            model, ((calls[0][0], unknown),), native_source_digest="trusted-native"
        )


def test_captured_generator_and_effective_role_correspondence_cannot_silently_drift():
    from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources

    model, calls = inputs()
    sources = capture_port_generator_sources()
    first = sources[0]
    changed = (replace(first, content=first.content + b"\n# changed"), *sources[1:])
    with pytest.raises(ValueError, match="differs from captured"):
        compile_data_operation_artifacts(
            model, calls, native_source_digest="trusted-native", generator_sources=changed
        )
    parameter = replace(calls[0][1].parameters[0], name="other")
    call = replace(calls[0][1], parameters=(parameter,))
    with pytest.raises(ValueError, match="role correspondence"):
        compile_data_operation_artifacts(
            model,
            ((calls[0][0], call),),
            native_source_digest="trusted-native",
            generator_sources=sources,
        )


@pytest.mark.parametrize(
    "change",
    [
        "primitive",
        "nullable",
        "resolved-nullable",
        "collection",
        "cardinality",
        "ordered",
        "default",
        "native-type",
        "backend",
    ],
)
def test_native_same_names_cannot_hide_semantic_type_or_completion_shape_mismatch(change):
    model, calls = inputs()
    call = calls[0][1]
    parameter = call.parameters[0]
    if change == "primitive":
        parameter = replace(parameter, resolved=OperationFieldType("integer", False, False))
    elif change == "nullable":
        parameter = replace(parameter, nullable=True)
    elif change == "resolved-nullable":
        parameter = replace(parameter, resolved=OperationFieldType("json_payload", True, False))
    elif change == "collection":
        parameter = replace(
            parameter, multivalued=True, resolved=OperationFieldType("json_payload", False, True)
        )
    elif change == "cardinality":
        call = replace(call, cardinality="many")
    elif change == "ordered":
        call = replace(call, ordered=True)
    elif change == "native-type":
        parameter = replace(parameter, native_type="integer")
    elif change == "backend":
        call = replace(call, backend="core")
    elif change == "default":
        parameter = replace(parameter, default_json="{}")
    call = replace(call, parameters=(parameter,))
    with pytest.raises(ValueError):
        compile_data_operation_artifacts(
            model, ((calls[0][0], call),), native_source_digest="trusted-native"
        )


@pytest.mark.parametrize("json_read", ["native", "json-text-v1"])
def test_generated_native_table_rows_own_nested_state_and_revalidate_instances(
    json_read, monkeypatch
):
    from pydantic import ValidationError

    from corpus_structure.semantic.operation_call_generation import render_call_bindings

    _, calls = inputs()
    call = replace(calls[0][1], result_mode="table", json_read=json_read)
    source = render_call_bindings(
        ((calls[0][0], call),),
        value_base=("corpus_structure.semantic.data_operation_ports", "DataOperationWireValue"),
        row_base=("corpus_structure.semantic.data_operation_ports", "DataOperationNativeRow"),
    )
    import sys
    from types import ModuleType

    module = ModuleType("corpus_structure.semantic._test_immutable_rows")
    module.__package__ = "corpus_structure.semantic"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    namespace: dict[str, Any] = module.__dict__
    exec(compile(source, "generated_rows.py", "exec"), namespace)
    materialize = namespace["materialize_read_demand_result"]
    if json_read == "native":
        original = {"nested": [1]}
        result = materialize((original,))
        original["nested"].append(2)
        result.payload["nested"].append(3)
        assert result.payload == {"nested": [1]}
    else:
        result = materialize(('{"nested":[1]}',))
        decoded = result.decoded_json_fields(operation="data.read_demand_result")
        decoded["payload"]["nested"].append(2)
        assert result.decoded_json_fields(operation="data.read_demand_result") == {
            "payload": {"nested": [1]}
        }
    cls = type(result)
    invalid = cls.model_construct(payload=object())
    with pytest.raises(ValidationError):
        cls.model_validate(invalid, strict=True)
