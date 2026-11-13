"""Independent closed-wire types and their effective model correspondence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
from corpus_structure.semantic.data_operation_wire import (
    KIND_PREFIX,
    checked_json_schema,
    validate_native_wire,
    wire_contracts,
    wire_kind_declarations,
    wire_role_kind,
)
from corpus_structure.semantic.identity import canonical_bytes, claim_source_item__data_operation__
from corpus_structure.semantic.types import SourceArtifact


def captured(content: bytes | None = None):
    source = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/data-operation-native.yaml"
    return (SourceArtifact("native/data-operation-protocol.yaml", source.read_bytes() if content is None else content),)


def wire_model(sources=None, binding=None):
    declaration: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
    declaration["id"] = "data.claim_data_request"
    declaration["roles"][0].update(name="request", parameter="payload", kind=wire_role_kind("claim_data_request", "input", sources))
    declaration["roles"][1].update(name="result", parameter="payload", kind=wire_role_kind("claim_data_request", "output", sources))
    declaration["binding"]["roles"] = ["request"]
    if binding is not None:
        declaration["binding"] = binding
    return compile_data_operations(declarations=(SourceArtifact("wire-declarations.json", canonical_bytes({"version": MODEL_VERSION, "operations": [declaration], "kinds": wire_kind_declarations(sources)})),))


@pytest.mark.parametrize("lease", ["3", True, None, 0, 86401])
def test_native_wire_integer_type_and_declared_limits_do_not_coerce(lease):
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_request", "input", {"request_id": "request:x", "holder": "worker", "lease_seconds": lease})


def test_exact_wire_fields_and_result_variants_are_explicit():
    payload = {"request_id": "request:x", "holder": "worker", "lease_seconds": 3}
    assert validate_native_wire("claim_data_request", "input", payload) == payload
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_request", "input", {**payload, "extra": 2})
    assert validate_native_wire("claim_data_request", "output", {"state": "no-work"}) == {"state": "no-work"}
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_request", "output", {"state": "claimed"})
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_request", "output", {"state": "no-work", "task_id": 4})


def test_shared_wire_contract_is_detached_and_has_only_local_resolved_references():
    contracts = wire_contracts(captured())
    assert len(contracts) == 12
    for directions in contracts.values():
        for schema in directions.values():
            checked_json_schema(schema)
    contracts["claim_data_request"]["input"]["definitions"].clear()
    assert wire_contracts(captured())["claim_data_request"]["input"]["definitions"]
    for schema in ({"$ref": "https://example.invalid/remote"}, {"$ref": "#/definitions/missing"}):
        with pytest.raises(ValueError):
            checked_json_schema(schema)


def test_effective_wire_record_has_the_same_constrained_field_graph():
    model = wire_model(captured())
    owner = KIND_PREFIX + "claim_data_request_request"
    kind = next(k for k in model.kinds if k.semantic_id == owner)
    assert kind.category == "class"
    assert json.loads(kind.facts)["json_schema"]
    lease = next(k for k in model.kinds if k.semantic_id == owner + "/property/lease_seconds")
    facts = json.loads(lease.facts)
    assert facts["range"] == "primitive:integer"
    assert facts["required"] is True
    assert facts["minimum"] == "1"
    assert facts["maximum"] == "86400"
    assert any(e.source == owner and e.target == lease.semantic_id and e.relation == "property" for e in model.edges)
    assert any(e.source == lease.semantic_id and e.target == "primitive:integer" and e.relation == "range" for e in model.edges)


def test_generated_boundaries_execute_the_captured_nested_wire_contract(monkeypatch):
    import sys
    from types import ModuleType
    from pydantic import ValidationError
    from corpus_structure.semantic.contracts import OperationCallBinding, OperationFieldBinding, OperationFieldType
    from corpus_structure.semantic.data_operation_artifacts import compile_data_operation_artifacts

    model = wire_model(captured())
    scalar_json = OperationFieldType("json_payload", False, False)
    parameter = OperationFieldBinding("payload", "native-wire", False, native_parameter="p_payload", resolved=scalar_json)
    result = OperationFieldBinding("payload", "native-wire", False, native_field="payload", resolved=scalar_json)
    call = OperationCallBinding("claim_data_request", "ops.claim_data_request", (parameter,), result_class="ClaimDataRequestResult", result_fields=(result,), cardinality="one", ordered=False, source_digest="wire-test", result_mode="json")
    artifact = compile_data_operation_artifacts(model, (("data.claim_data_request", call),), native_source_digest="wire-test")
    module = ModuleType("corpus_structure.semantic._test_captured_wire")
    module.__package__ = "corpus_structure.semantic"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(artifact.calls, "captured_wire.py", "exec"), module.__dict__)
    request = module.__dict__["_claim_data_requestRequest"]
    result_type = module.__dict__["ClaimDataRequestResult"]
    checked = request.model_validate_json('{"payload":{"request_id":"request:x","holder":"worker","lease_seconds":3}}', strict=True)
    assert checked.payload["lease_seconds"] == 3
    with pytest.raises(ValidationError):
        request.model_validate_json('{"payload":{"request_id":"request:x","holder":"worker","lease_seconds":"3"}}', strict=True)
    assert result_type.model_validate_json('{"payload":{"state":"no-work"}}', strict=True).payload == {"state": "no-work"}
    with pytest.raises(ValidationError):
        result_type.model_validate_json('{"payload":{"state":"claimed"}}', strict=True)


def test_nested_support_and_product_member_attributes_cannot_hide_type_coercion():
    completion: dict[str, Any] = {
        "request_id": "request:x", "generation": 1, "task_id": 1, "attempt": 1,
        "holder": "worker", "runtime_id": "runtime:x",
        "completion": {
            "outcome": "addressed", "implementation_revision": "implementation:x",
            "inputs": [], "support": [{"derivation_id": "derivation:x", "role": "source", "position": 0}],
            "outputs": [{"role": "result", "position": 0, "multiplicity": 1,
                "product": {"kind_contract": "kind:x", "body": ["string", "answer"], "members": []}}],
        },
    }
    assert validate_native_wire("retain_data_completion_intent", "input", completion)["completion"]["outcome"] == "addressed"
    invalid = copy.deepcopy(completion)
    invalid["completion"]["support"][0]["position"] = "0"
    with pytest.raises(ValueError, match="schema"):
        validate_native_wire("retain_data_completion_intent", "input", invalid)
    invalid = copy.deepcopy(completion)
    invalid["completion"]["outputs"][0]["product"]["members"] = [{"member_id": "m", "body": ["mapping", []], "choices": [{"choice_group": "g", "alternative": "a", "selected": "true"}]}]
    with pytest.raises(ValueError, match="schema"):
        validate_native_wire("retain_data_completion_intent", "input", invalid)


def test_unrelated_wire_definition_does_not_contaminate_rooted_kind_identity():
    original = captured()
    document = yaml.safe_load(original[0].content)
    document["definitions"]["unused_extension"] = {"type": "object", "properties": {"new": {"type": "boolean"}}, "additionalProperties": False}
    changed = captured(yaml.safe_dump(document).encode())
    before, after = wire_model(original), wire_model(changed)
    owner = KIND_PREFIX + "claim_data_request_request"
    def fingerprint(model):
        return next(i.key for i in model.identities if i.owner == owner and i.domain == "kind")
    assert fingerprint(before) == fingerprint(after)



@pytest.mark.parametrize("field,invalid,valid", [("lease_seconds", 0, 3), ("holder", "", "worker")])
def test_wire_predicate_literals_reuse_the_exact_constrained_field_authority(field, invalid, valid):
    from corpus_structure.semantic.types import PreparationError
    owner = KIND_PREFIX + "claim_data_request_request"
    binding = {"operator": "literal", "fields": [{"role": "request", "projection": owner, "field": field}], "value": invalid}
    with pytest.raises(PreparationError, match="typed binding literal"):
        wire_model(captured(), binding)
    binding["value"] = valid
    assert wire_model(captured(), binding).operations
