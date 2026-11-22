"""Independent closed-wire types and their effective model correspondence."""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from typing import Any

import pytest
import yaml

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_version import MODEL_VERSION
from corpus_structure.semantic.data_operation_wire import (
    KIND_PREFIX,
    ExactJSONValue,
    checked_json_schema,
    validate_native_wire,
    wire_contracts,
    wire_kind_declarations,
    wire_role_kind,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import SourceArtifact
from semantic.data_operation_declaration_support import contract
from semantic.data_operation_port_support import captured


def test_acquired_record_interpretation_uses_declared_roles_without_revalidation(monkeypatch):
    from corpus_structure.semantic import data_operation_wire as wire
    from corpus_structure.semantic.data_operation_json import native_json_loads
    from corpus_structure.semantic.schema_validation import PreparedSchemaValidator

    def unexpected_validation(*args):
        raise AssertionError("acquired record interpretation must not repeat structural admission")

    monkeypatch.setattr(PreparedSchemaValidator, "validate", unexpected_validation)
    original = native_json_loads(
        b'{"selection":{"analyzed_scope":{"fraction":0.123456789012345678901},"filter":{"analyzed_scope":{"fraction":0.123456789012345678901}}}}'
    )
    interpreted = wire.interpret_wire_record("population_evidence", original)
    assert interpreted["selection"]["analyzed_scope"]["fraction"] == Decimal(
        "0.123456789012345678901"
    )
    assert interpreted["selection"]["filter"]["analyzed_scope"]["fraction"] == 0.12345678901234568
    assert type(interpreted["selection"]["filter"]["analyzed_scope"]["fraction"]) is float
    interpreted["selection"]["analyzed_scope"].clear()
    assert original["selection"]["analyzed_scope"] == {
        "fraction": Decimal("0.123456789012345678901")
    }


def test_ambient_protocol_is_prepared_once_while_results_remain_detached(monkeypatch):
    from corpus_structure.caches import clear
    from corpus_structure.model.compiled import model_request_scope
    from corpus_structure.semantic import data_operation_wire as wire
    from corpus_structure.semantic import native_protocol_model

    prepare = native_protocol_model._prepare_protocol_content
    preparations = []

    def observed(sources):
        preparations.append(sources)
        return prepare(sources)

    clear("model_entries")
    with model_request_scope():
        monkeypatch.setattr(native_protocol_model, "_prepare_protocol_content", observed)
        first = wire.wire_contracts()
        first["claim_data_requests"]["input"].clear()
        assert wire.wire_role_kind("claim_data_requests", "input").endswith(
            "claim_data_requests_request"
        )
        payload = {
            "items": [{"request_id": "request:x", "generation": 1}],
            "holder": "worker",
            "lease_seconds": 3,
        }
        assert wire.validate_native_wire("claim_data_requests", "input", payload) == payload
        assert wire.wire_contracts()["claim_data_requests"]["input"]
        assert preparations == [None]


def test_ambient_validation_and_role_lookup_survive_captured_cache_eviction(monkeypatch):
    from corpus_structure.semantic import data_operation_wire as wire

    payload = {
        "items": [{"request_id": "request:x", "generation": 1}],
        "holder": "worker",
        "lease_seconds": 3,
    }
    assert wire.validate_native_wire("claim_data_requests", "input", payload) == payload
    wire._prepared_protocol.cache_clear()
    wire._validator.cache_clear()

    def unexpected_preparation(*args, **kwargs):
        raise AssertionError("ambient operation repeated preparation")

    monkeypatch.setattr(wire, "_prepared_protocol", unexpected_preparation)
    monkeypatch.setattr(wire, "_validator", unexpected_preparation)
    assert wire.validate_native_wire("claim_data_requests", "input", payload) == payload
    assert wire.wire_role_kind("claim_data_requests", "input") == (
        KIND_PREFIX + "claim_data_requests_request"
    )
    with pytest.raises(ValueError, match="schema"):
        wire.validate_native_wire(
            "claim_data_requests",
            "input",
            {**payload, "items": [{"request_id": "request:x", "generation": "1"}]},
        )


def test_prepared_wire_validator_owns_its_schema_after_caller_mutation_and_eviction(monkeypatch):
    from corpus_structure.semantic import data_operation_wire as wire

    schema = {"type": "integer", "minimum": 2}
    validate = wire.prepare_wire_schema(schema)
    schema.clear()
    wire._validator.cache_clear()

    def unexpected_preparation(*args, **kwargs):
        raise AssertionError("prepared call rebuilt its validator")

    monkeypatch.setattr(wire, "_validator", unexpected_preparation)
    assert validate(3) == 3
    with pytest.raises(ValueError, match="schema"):
        validate(1)
    with pytest.raises(ValueError, match="schema"):
        validate("3")


def test_prepared_schema_requires_declared_dialect_and_cannot_retrieve_remote_refs():
    from referencing.exceptions import Unresolvable

    from corpus_structure.semantic.schema_validation import prepared_schema_validator

    with pytest.raises(ValueError, match="explicit supported dialect"):
        prepared_schema_validator(b'{"type":"integer"}')
    validator = prepared_schema_validator(
        b'{"$schema":"https://json-schema.org/draft/2020-12/schema",'
        b'"$ref":"https://unavailable.invalid/schema"}'
    )
    with pytest.raises(Unresolvable):
        validator.validate(1)


def test_prepared_schema_resources_are_captured_and_participate_in_cache_identity():
    from jsonschema import ValidationError

    from corpus_structure.semantic.schema_validation import prepared_schema_validator

    root = b'{"$schema":"https://json-schema.org/draft/2020-12/schema","$ref":"urn:captured:count"}'
    one = b'{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"integer","minimum":1}'
    two = one.replace(b'"minimum":1', b'"minimum":2')
    first = prepared_schema_validator(root, (("urn:captured:count", one),))
    second = prepared_schema_validator(root, (("urn:captured:count", two),))
    first.validate(1)
    with pytest.raises(ValidationError):
        second.validate(1)
    with pytest.raises(ValueError, match="duplicate captured"):
        prepared_schema_validator(root, (("urn:captured:count", one), ("urn:captured:count", two)))


def test_schema_numeric_adapter_preserves_limits_literals_and_captured_reference_classification():
    from decimal import Decimal

    from jsonschema import ValidationError

    from corpus_structure.semantic.schema_validation import prepared_schema_validator

    schema = b'{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"number","minimum":0.1,"maximum":0.3,"multipleOf":0.1}'
    validator = prepared_schema_validator(schema)
    validator.validate(0.1)
    validator.validate(0.3)
    with pytest.raises(ValidationError):
        validator.validate(Decimal("0.30000000000000000000000001"))
    with pytest.raises(ValidationError):
        validator.validate(Decimal("0.10000000000000000000000001"))
    literal = prepared_schema_validator(
        b'{"$schema":"http://json-schema.org/draft-07/schema#","enum":[0.1]}'
    )
    literal.validate(0.1)
    with pytest.raises(ValidationError):
        literal.validate(Decimal("0.10000000000000000000000001"))
    root = (
        b'{"$schema":"https://json-schema.org/draft/2020-12/schema","$ref":"urn:captured:integer"}'
    )
    integer = b'{"$schema":"http://json-schema.org/draft-07/schema#","type":"integer"}'
    with pytest.raises(ValidationError):
        prepared_schema_validator(root, (("urn:captured:integer", integer),)).validate(
            Decimal("1.000000000000000000001")
        )


def test_native_pydantic_generator_retains_tuple_elements_and_literal_payloads():
    from jsonschema import Draft7Validator, ValidationError
    from pydantic import TypeAdapter

    from corpus_structure.semantic.data_operation_wire import NativeJsonSchema

    schema = TypeAdapter(tuple[int, str]).json_schema(schema_generator=NativeJsonSchema)
    assert schema["items"] == [{"type": "integer"}, {"type": "string"}]
    validator = Draft7Validator(schema)
    validator.validate([1, "ready"])
    with pytest.raises(ValidationError):
        validator.validate([1, 2])


def controlled_wire_declaration():
    declaration: dict[str, Any] = contract(
        id="controlled.claim_data_requests",
        profile="command",
        behavior="controlled-native-wire-v1",
        invariants=[],
        outcomes=["success"],
        transitions=[],
        state_dimensions=[],
        effects=[
            {
                "name": "controlled-wire-effect",
                "authorization": ["controlled-native-purpose"],
                "idempotency": "request-generation-and-holder",
                "fulfillment": "native-transaction",
            }
        ],
    )
    return declaration


def wire_model(sources=None, binding=None):
    declaration = controlled_wire_declaration()
    declaration["roles"][0].update(
        name="request",
        parameter="payload",
        kind=wire_role_kind("claim_data_requests", "input", sources),
    )
    declaration["roles"][0]["support"]["coverage"]["role"] = "request"
    declaration["roles"][1].update(
        name="result",
        parameter="payload",
        kind=wire_role_kind("claim_data_requests", "output", sources),
    )
    declaration["binding"]["roles"] = ["request"]
    if binding is not None:
        declaration["binding"] = binding
    return compile_data_operations(
        declarations=(
            SourceArtifact(
                "wire-declarations.json",
                canonical_bytes(
                    {
                        "version": MODEL_VERSION,
                        "operations": [declaration],
                        "kinds": wire_kind_declarations(sources),
                    }
                ),
            ),
        )
    )


@pytest.mark.parametrize("lease", ["3", True, None, 0, 86401])
def test_native_wire_integer_type_and_declared_limits_do_not_coerce(lease):
    with pytest.raises(ValueError):
        validate_native_wire(
            "claim_data_requests",
            "input",
            {
                "items": [{"request_id": "request:x", "generation": 1}],
                "holder": "worker",
                "lease_seconds": lease,
            },
        )


def test_exact_wire_fields_and_result_variants_are_explicit():
    payload = {
        "items": [{"request_id": "request:x", "generation": 1}],
        "holder": "worker",
        "lease_seconds": 3,
    }
    assert validate_native_wire("claim_data_requests", "input", payload) == payload
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_requests", "input", {**payload, "extra": 2})
    assert validate_native_wire(
        "claim_data_requests", "output", {"items": [{"state": "no-work"}]}
    ) == {"items": [{"state": "no-work"}]}
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_requests", "output", {"items": [{"state": "claimed"}]})
    with pytest.raises(ValueError):
        validate_native_wire(
            "claim_data_requests", "output", {"items": [{"state": "no-work", "task_id": 4}]}
        )


@pytest.mark.parametrize("direction", ["input", "output"])
def test_source_initialization_wire_requires_only_exact_project_and_release(direction):
    payload = {"project_id": "project:originals", "release_id": "release:source"}
    assert validate_native_wire("initialize_source_project", direction, payload) == payload
    for invalid in (
        {"project_id": payload["project_id"]},
        {"release_id": payload["release_id"]},
        {**payload, "realization_id": "legacy-empty-realization"},
    ):
        with pytest.raises(ValueError):
            validate_native_wire("initialize_source_project", direction, invalid)


def test_shared_wire_contract_is_detached_and_has_only_local_resolved_references():
    contracts = wire_contracts(captured())
    for directions in contracts.values():
        for schema in directions.values():
            checked_json_schema(schema)
    contracts["claim_data_requests"]["input"]["definitions"].clear()
    assert wire_contracts(captured())["claim_data_requests"]["input"]["definitions"]
    for schema in ({"$ref": "https://example.invalid/remote"}, {"$ref": "#/definitions/missing"}):
        with pytest.raises(ValueError):
            checked_json_schema(schema)


def test_effective_wire_record_has_the_same_constrained_field_graph():
    model = wire_model(captured())
    owner = KIND_PREFIX + "claim_data_requests_request"
    kind = next(k for k in model.kinds if k.semantic_id == owner)
    assert kind.category == "class"
    assert json.loads(kind.facts)["json_schema"]
    lease = next(k for k in model.kinds if k.semantic_id == owner + "/property/lease_seconds")
    facts = json.loads(lease.facts)
    assert facts["range"] == "primitive:integer"
    assert facts["required"] is True
    assert facts["minimum"] == "1"
    assert facts["maximum"] == "86400"
    assert any(
        e.source == owner and e.target == lease.semantic_id and e.relation == "property"
        for e in model.edges
    )
    assert any(
        e.source == lease.semantic_id and e.target == "primitive:integer" and e.relation == "range"
        for e in model.edges
    )


def test_generated_boundaries_execute_the_captured_nested_wire_contract(monkeypatch):
    import sys
    from types import ModuleType

    from pydantic import ValidationError

    from corpus_structure.semantic import data_operation_wire as wire
    from corpus_structure.semantic.data_operation_artifacts import compile_data_operation_artifacts
    from corpus_structure.semantic.native_call_contracts import (
        OperationCallBinding,
        OperationFieldBinding,
        OperationFieldType,
    )

    model = wire_model(captured())
    scalar_json = OperationFieldType("json_payload", False, False)
    parameter = OperationFieldBinding(
        "payload", "native-wire", False, native_parameter="p_payload", resolved=scalar_json
    )
    result = OperationFieldBinding(
        "payload", "native-wire", False, native_field="payload", resolved=scalar_json
    )
    call = OperationCallBinding(
        "controlled_wire",
        "ops.controlled_wire",
        (parameter,),
        result_class="ControlledWireResult",
        result_fields=(result,),
        cardinality="one",
        ordered=False,
        source_digest="wire-test",
        result_mode="json",
    )
    artifact = compile_data_operation_artifacts(
        model, (("controlled.claim_data_requests", call),), native_source_digest="wire-test"
    )
    module = ModuleType("corpus_structure.semantic._test_captured_wire")
    module.__package__ = "corpus_structure.semantic"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    prepare = wire.prepare_wire_schema
    preparations = []

    def observed(schema):
        preparations.append(schema)
        return prepare(schema)

    monkeypatch.setattr(wire, "prepare_wire_schema", observed)
    exec(compile(artifact.calls, "captured_wire.py", "exec"), module.__dict__)
    assert len(preparations) == 2
    wire._validator.cache_clear()

    def unexpected_preparation(*args, **kwargs):
        raise AssertionError("generated call repeated schema preparation")

    monkeypatch.setattr(wire, "_validator", unexpected_preparation)
    request = module.__dict__["_controlled_wireRequest"]
    result_type = module.__dict__["ControlledWireResult"]
    checked = request.model_validate_json(
        '{"payload":{"items":[{"request_id":"request:x","generation":1}],"holder":"worker","lease_seconds":3}}',
        strict=True,
    )
    assert checked.payload["lease_seconds"] == 3
    with pytest.raises(ValidationError):
        request.model_validate_json(
            '{"payload":{"items":[{"request_id":"request:x","generation":1}],"holder":"worker","lease_seconds":"3"}}',
            strict=True,
        )
    assert result_type.model_validate_json(
        '{"payload":{"items":[{"state":"no-work"}]}}', strict=True
    ).payload == {"items": [{"state": "no-work"}]}
    with pytest.raises(ValidationError):
        result_type.model_validate_json('{"payload":{"items":[{"state":"claimed"}]}}', strict=True)


def test_nested_support_and_product_member_attributes_cannot_hide_type_coercion():
    completion: dict[str, Any] = {
        "request_id": "request:x",
        "generation": 1,
        "task_id": 1,
        "attempt": 1,
        "holder": "worker",
        "runtime_id": "runtime:x",
        "completion": {
            "outcome": "addressed",
            "implementation_revision": "implementation:x",
            "inputs": [],
            "support": [{"derivation_id": "derivation:x", "role": "source", "position": 0}],
            "outputs": [
                {
                    "role": "result",
                    "position": 0,
                    "multiplicity": 1,
                    "product": {
                        "kind_contract": "kind:x",
                        "body": ["string", "answer"],
                        "members": [],
                    },
                }
            ],
        },
    }
    assert (
        validate_native_wire("retain_data_completion_intent", "input", completion)["completion"][
            "outcome"
        ]
        == "addressed"
    )
    invalid = copy.deepcopy(completion)
    invalid["completion"]["support"][0]["position"] = "0"
    with pytest.raises(ValueError, match="schema"):
        validate_native_wire("retain_data_completion_intent", "input", invalid)
    invalid = copy.deepcopy(completion)
    invalid["completion"]["outputs"][0]["product"]["members"] = [
        {
            "member_id": "m",
            "kind_contract": "kind:member",
            "context": {
                "subject": "member:m",
                "original_source": "source:x",
                "analyzed_scope": {},
                "subject_definition": "original-source-view",
            },
            "body": ["mapping", []],
        }
    ]
    assert validate_native_wire("retain_data_completion_intent", "input", invalid)
    member = invalid["completion"]["outputs"][0]["product"]["members"][0]
    member["context"]["subject_definition"] = 1
    with pytest.raises(ValueError, match="schema"):
        validate_native_wire("retain_data_completion_intent", "input", invalid)


def test_unrelated_wire_definition_does_not_contaminate_rooted_kind_identity():
    original = captured()
    document = yaml.safe_load(original[0].content)
    document["definitions"]["unused_extension"] = {
        "type": "object",
        "properties": {"new": {"type": "boolean"}},
        "additionalProperties": False,
    }
    changed = captured(yaml.safe_dump(document).encode())
    before, after = wire_model(original), wire_model(changed)
    owner = KIND_PREFIX + "claim_data_requests_request"

    def fingerprint(model):
        return next(i.key for i in model.identities if i.owner == owner and i.domain == "kind")

    assert fingerprint(before) == fingerprint(after)


@pytest.mark.parametrize("field,invalid,valid", [("lease_seconds", 0, 3), ("holder", "", "worker")])
def test_wire_predicate_literals_reuse_the_exact_constrained_field_authority(field, invalid, valid):
    from corpus_structure.semantic.types import PreparationError

    owner = KIND_PREFIX + "claim_data_requests_request"
    binding = {
        "operator": "literal",
        "fields": [{"role": "request", "projection": owner, "field": field}],
        "value": invalid,
    }
    with pytest.raises(PreparationError, match="typed binding literal"):
        wire_model(captured(), binding)
    binding["value"] = valid
    assert wire_model(captured(), binding).operations


def test_acquisition_read_declares_its_effect_profile_and_purposes_explicitly():
    from corpus_structure.semantic.data_operation_wire import wire_operations

    operations = {operation["name"]: operation for operation in wire_operations(captured())}
    read = operations["read_demand_result"]
    assert read["profile"] == "command"
    assert read["purposes"] == ["read", "write", "evaluate"]
    assert operations["inspect_data_completion"]["profile"] == "read"
    assert operations["inspect_data_completion"]["purposes"] == ["read", "write", "evaluate"]
    assert operations["publish_data_derivation"]["purposes"] == ["write", "evaluate"]
    document = yaml.safe_load(captured()[0].content)
    document["operations"][0]["purposes"] = []
    with pytest.raises(ValueError, match="purpose"):
        wire_operations(captured(yaml.safe_dump(document).encode()))


def frozen_selection():
    return {
        "version": "data-demand-intent-v2",
        "model": "a" * 64,
        "roots": [],
        "targets": ["operation:x"],
        "operations": [
            {
                "operation": "operation:x",
                "parameters": {},
                "parameter_meaning": ["mapping", []],
                "choices": {},
                "replicate": None,
                "dependencies": [],
                "definition": "definition:x",
                "recipe": "recipe:x",
                "eligibility": "eligibility:x",
            }
        ],
        "root_operations": ["operation:x"],
        "discovery": [],
        "inference": "inference:x",
        "execution_profile": "execution:x",
    }


def test_read_receipt_lookup_and_cursor_pins_have_distinct_explicit_shapes():
    assert (
        validate_native_wire(
            "read_demand_result", "input", {"demand_id": "demand:x", "read_id": "read:x"}
        )["read_id"]
        == "read:x"
    )
    with pytest.raises(ValueError):
        validate_native_wire(
            "read_demand_result", "input", {"demand_id": "demand:x", "read_snapshot": "1:1:"}
        )
    cursor = {
        "demand_id": "demand:x",
        "read_id": "read:x",
        "after": "obligation:x",
        "selection": frozen_selection(),
        "trust_snapshot": {},
        "limit": 5,
    }
    assert validate_native_wire("read_demand_result", "input", cursor)["limit"] == 5
    cursor.pop("read_id")
    with pytest.raises(ValueError):
        validate_native_wire("read_demand_result", "input", cursor)
    result: dict[str, Any] = {
        "demand_id": "demand:x",
        "selection": frozen_selection(),
        "intent": frozen_selection(),
        "root": [],
        "project_id": "project:x",
        "release_id": "release:x",
        "runtime_id": "runtime:x",
        "trust_snapshot": {},
        "scope": {},
        "uses": [],
        "obligations": [],
        "populations": [],
        "continuation": None,
        "view": "frontier",
    }
    with pytest.raises(ValueError):
        validate_native_wire("read_demand_result", "output", result)
    result.update(read_id="read:x", read_snapshot="1:1:", frontier_at="2026-11-13T12:00:00+00:00")
    assert validate_native_wire("read_demand_result", "output", result)["read_snapshot"] == "1:1:"


def test_native_attachment_binding_requires_the_authenticated_read_receipt_reference():
    binding = {
        "inputs": [],
        "support": [],
        "parameters": ["mapping", []],
        "request_inputs": ["mapping", []],
        "inference": "inference:x",
        "populations": [],
    }
    request = {
        "obligation_id": "obligation:x",
        "request_meaning": ["mapping", []],
        "binding": binding,
        "replicate": None,
    }
    with pytest.raises(ValueError):
        validate_native_wire(
            "attach_data_requests", "input", {"read_id": "read:x", "items": [request]}
        )
    binding["read_id"] = "read:x"
    assert (
        validate_native_wire(
            "attach_data_requests", "input", {"read_id": "read:x", "items": [request]}
        )["items"][0]["binding"]["read_id"]
        == "read:x"
    )


def member_completion(member, *, domain_body=None):
    from corpus_structure.semantic.data_operation_values import semantic_value

    return {
        "request_id": "request:x",
        "generation": 1,
        "task_id": 1,
        "attempt": 1,
        "holder": "worker",
        "runtime_id": "runtime:x",
        "completion": {
            "outcome": "addressed",
            "implementation_revision": "implementation:x",
            "inputs": [],
            "support": [],
            "outputs": [
                {
                    "role": "result",
                    "position": 0,
                    "multiplicity": 1,
                    "product": {
                        "kind_contract": "kind:x",
                        "body": semantic_value(
                            {
                                "members": [
                                    {
                                        "member_id": member["member_id"],
                                        "kind_contract": member.get("kind_contract"),
                                        "context": member.get("context"),
                                        "body": {} if domain_body is None else domain_body,
                                    }
                                ]
                            }
                        ),
                        "members": [member],
                    },
                }
            ],
        },
    }


def test_member_context_is_required_and_does_not_reinterpret_domain_subject():
    member = {
        "member_id": "member:x",
        "kind_contract": "kind:member",
        "context": {
            "subject": "occurrence:x",
            "original_source": "source:x",
            "analyzed_scope": {"page": 2},
            "subject_definition": "original-source-view",
        },
        "body": ["mapping", [["subject", ["string", "linguistic-subject"]]]],
    }
    accepted = validate_native_wire(
        "retain_data_completion_intent",
        "input",
        member_completion(member, domain_body={"subject": "linguistic-subject"}),
    )
    retained = accepted["completion"]["outputs"][0]["product"]["members"][0]
    assert retained["context"]["subject"] == "occurrence:x"
    assert retained["body"] == ["mapping", [["subject", ["string", "linguistic-subject"]]]]
    # Physical metadata is not demanded inside the domain payload.
    member["body"] = ["integer", "7"]
    assert validate_native_wire(
        "retain_data_completion_intent", "input", member_completion(member, domain_body=7)
    )
    member.pop("context")
    with pytest.raises(ValueError):
        validate_native_wire("retain_data_completion_intent", "input", member_completion(member))


@pytest.mark.parametrize(
    "name,value",
    [
        ("endpoints", [{"scope": "local", "role": "object", "member_id": "member:other"}]),
        ("choices", [{"choice_group": "g", "alternative": "a", "selected": True}]),
    ],
)
def test_product_members_refuse_retired_envelope_reference_metadata(name, value):
    member = {
        "member_id": "member:x",
        "kind_contract": "kind:member",
        "context": {
            "subject": "occurrence:x",
            "original_source": "source:x",
            "analyzed_scope": {},
            "subject_definition": "original-source-view",
        },
        "body": ["mapping", []],
    }
    member[name] = value
    with pytest.raises(ValueError, match="Additional properties are not allowed"):
        validate_native_wire("retain_data_completion_intent", "input", member_completion(member))


def test_member_context_remains_typed_in_effective_fields():
    model = wire_model(captured())
    context = next(
        k for k in model.kinds if k.semantic_id == KIND_PREFIX + "product_member/property/context"
    )
    assert json.loads(context.facts)["required"] is True
    assert json.loads(context.facts)["range"] == KIND_PREFIX + "member_context"


def test_frontier_and_products_views_expose_explicit_body_states():
    product: dict[str, Any] = {
        "role": "result",
        "position": 0,
        "multiplicity": 1,
        "product_id": "product:x",
        "member_id": None,
        "kind_contract": "kind:x",
        "subject": "subject:x",
        "original_source": "source:x",
        "analyzed_scope": {},
        "body_state": "not_requested",
        "subject_definition": "original-source-view",
    }
    selection = {
        "inputs": [],
        "support": [],
        "parameters": ["mapping", []],
        "request_inputs": ["mapping", []],
        "inference": "inference:x",
        "populations": [],
        "read_id": "read:x",
    }
    result = {
        "demand_id": "demand:x",
        "selection": frozen_selection(),
        "intent": frozen_selection(),
        "root": [],
        "project_id": "project:x",
        "release_id": "release:x",
        "runtime_id": "runtime:x",
        "trust_snapshot": {},
        "scope": {},
        "obligations": [],
        "populations": [],
        "continuation": None,
        "view": "frontier",
        "read_id": "read:x",
        "read_snapshot": "1:1:",
        "frontier_at": "2026-11-13T12:00:00+00:00",
        "uses": [
            {
                "use_id": "use:x",
                "obligation_id": "obligation:x",
                "fate": "fulfilled",
                "historical_fate": "fulfilled",
                "request_id": "request:x",
                "generation": 1,
                "derivation_id": "derivation:x",
                "selection": selection,
                "trust_snapshot": {},
                "semantic_outcome": "addressed",
                "completion_state": "success",
                "products": [product],
            }
        ],
    }
    assert (
        validate_native_wire("read_demand_result", "output", result)["uses"][0]["products"][0][
            "body_state"
        ]
        == "not_requested"
    )
    product["body"] = ["string", "answer"]
    with pytest.raises(ValueError):
        validate_native_wire("read_demand_result", "output", result)
    product["body_state"] = "present"
    with pytest.raises(ValueError):
        validate_native_wire("read_demand_result", "output", result)
    result["view"] = "products"
    assert validate_native_wire("read_demand_result", "output", result)["uses"][0]["products"][0][
        "body"
    ] == ["string", "answer"]
    product.pop("body")
    with pytest.raises(ValueError):
        validate_native_wire("read_demand_result", "output", result)


def test_object_constraints_do_not_erase_common_fields_from_the_effective_graph():
    model = wire_model(captured())
    fields = {kind.semantic_id for kind in model.kinds}
    assert KIND_PREFIX + "inspect_data_completion_request/property/intent_id" in fields
    assert KIND_PREFIX + "result_product/property/product_id" in fields
    assert KIND_PREFIX + "result_product/property/body_state" in fields


def test_member_wire_carries_a_distinct_authenticated_kind_contract():
    member: dict[str, Any] = {
        "member_id": "member:x",
        "kind_contract": "kind:member",
        "context": {
            "subject": "occurrence:x",
            "original_source": "source:x",
            "analyzed_scope": {},
            "subject_definition": "original-source-view",
        },
        "body": ["integer", "7"],
    }
    request = member_completion(member, domain_body=7)
    product = request["completion"]["outputs"][0]["product"]
    assert product["kind_contract"] != member["kind_contract"]
    checked = validate_native_wire("retain_data_completion_intent", "input", request)
    assert (
        checked["completion"]["outputs"][0]["product"]["members"][0]["kind_contract"]
        == "kind:member"
    )
    member.pop("kind_contract")
    with pytest.raises(ValueError):
        validate_native_wire(
            "retain_data_completion_intent", "input", member_completion(member, domain_body=7)
        )


def test_custom_local_schema_definition_never_relabels_an_existing_wire_kind():
    from corpus_structure.semantic.types import PreparationError

    # The names collide while the actual definitions and nominal owners differ.
    wire_payload = {
        "id": KIND_PREFIX + "Payload",
        "scope": "native-wire",
        "json_schema": {
            "type": "object",
            "properties": {"wire_flag": {"type": "boolean"}},
            "required": ["wire_flag"],
            "additionalProperties": False,
        },
    }
    custom = {
        "id": "urn:test:CustomRequest",
        "json_schema": {
            "type": "object",
            "properties": {"payload": {"$ref": "#/definitions/Payload"}},
            "required": ["payload"],
            "additionalProperties": False,
            "definitions": {
                "Payload": {
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                    "required": ["value"],
                    "additionalProperties": False,
                }
            },
        },
    }
    declaration = controlled_wire_declaration()
    declaration["roles"][0]["kind"] = custom["id"]
    source = SourceArtifact(
        "custom-wire-collision.json",
        canonical_bytes(
            {"version": MODEL_VERSION, "operations": [declaration], "kinds": [wire_payload, custom]}
        ),
    )
    with pytest.raises(
        PreparationError, match="unsupported nominal JSON Schema property projection"
    ):
        compile_data_operations(declarations=(source,))


def test_request_renewal_wire_requires_exact_fence_and_bounded_duration():
    payload = {
        "request_id": "request:one",
        "generation": 2,
        "task_id": 3,
        "attempt": 4,
        "holder": "producer",
        "lease_seconds": 30,
    }
    assert validate_native_wire("renew_data_request", "input", payload) == payload
    for altered in (
        {key: value for key, value in payload.items() if key != "generation"},
        {**payload, "lease_seconds": 0},
        {**payload, "lease_seconds": 86401},
        {**payload, "attempt": True},
        {**payload, "run_id": 1},
    ):
        with pytest.raises(ValueError):
            validate_native_wire("renew_data_request", "input", altered)


def test_cancel_demand_wire_requires_reason_and_never_claims_physical_retirement():
    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    assert (
        validate_native_wire(
            "cancel_data_demand",
            "input",
            {
                "demand_id": "demand:one",
                "reason": "operator cancelled",
            },
        )["reason"]
        == "operator cancelled"
    )
    with pytest.raises(ValueError):
        validate_native_wire(
            "cancel_data_demand",
            "input",
            {
                "demand_id": "demand:one",
                "reason": "",
            },
        )
    result: dict[str, Any] = {
        "demand_id": "demand:one",
        "state": "cancelled",
        "reason": "operator cancelled",
        "requests": [
            {
                "request_id": "request:one",
                "generation": 1,
                "task_id": 1,
                "interest": "shared",
                "physical_retirement": "unconfirmed",
            }
        ],
    }
    assert validate_native_wire("cancel_data_demand", "output", result) == result
    result["requests"][0]["physical_retirement"] = "retired"
    with pytest.raises(ValueError):
        validate_native_wire("cancel_data_demand", "output", result)


def test_selected_population_wire_accepts_only_authenticated_parent_and_frozen_filter_context():
    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    request = {
        "obligation_id": "obligation:one",
        "population_name": "selected-items",
        "parent_population_id": "population:parent",
        "read_id": "read:one",
    }
    assert validate_native_wire("select_data_population", "input", request) == request
    for key, value in (("filter", {}), ("parameters", {}), ("members", []), ("complete", True)):
        with pytest.raises(ValueError):
            validate_native_wire("select_data_population", "input", {**request, key: value})
    selection = {
        "parent_population_id": "population:parent",
        "read_id": "read:one",
        "obligation_id": "obligation:one",
        "operation_id": "urn:consumer",
        "subject": "doc:one",
        "original_source": "source:one",
        "analyzed_scope": {},
        "role": "items",
        "definition": "definition:one",
        "eligibility": "eligibility:one",
        "filter": {"operator": "all", "children": []},
        "parameter_meaning": ["mapping", []],
        "choices": {},
        "subject_definition": "original-source-view",
    }
    result = {
        "population_id": "population:selected",
        "name": "selected-items",
        "semantic_key": "population-value:one",
        "members": [],
        "complete": True,
        "inserted_obligations": 0,
        "evidence": {
            "product_id": "product:parent",
            "derivation_id": "derivation:parent",
            "member_role": "members",
            "trust_snapshot": {},
            "population_id": "population:selected",
            "admission_use_id": "use:parent",
            "selection": selection,
        },
    }
    assert validate_native_wire("select_data_population", "output", result) == result
    del selection["parent_population_id"]
    with pytest.raises(ValueError):
        validate_native_wire("select_data_population", "output", result)


def test_renewal_loss_is_typed_and_cannot_claim_a_renewed_lease():
    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    fence = {
        "request_id": "request:one",
        "generation": 1,
        "task_id": 2,
        "attempt": 3,
        "holder": "owner",
    }
    for reason in ("fence", "cancelled", "revoked", "support-unavailable"):
        result = {**fence, "state": "lost", "reason": reason}
        assert validate_native_wire("renew_data_request", "output", result) == result
        with pytest.raises(ValueError):
            validate_native_wire("renew_data_request", "output", {**result, "lease_until": "now"})
    with pytest.raises(ValueError):
        validate_native_wire("renew_data_request", "output", {**fence, "state": "lost"})


def test_attempt_release_requires_confirmed_physical_retirement_and_closed_failure():
    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    request = {
        "request_id": "request:one",
        "generation": 1,
        "task_id": 2,
        "attempt": 3,
        "holder": "owner",
        "physical_retirement": "confirmed",
        "failure": {"code": "compute-error", "message": "input rejected"},
    }
    assert validate_native_wire("release_data_attempt", "input", request) == request
    for state in ("unknown", "unconfirmed", "in-flight"):
        with pytest.raises(ValueError):
            validate_native_wire(
                "release_data_attempt",
                "input",
                {
                    **request,
                    "physical_retirement": state,
                },
            )
    with pytest.raises(ValueError):
        validate_native_wire(
            "release_data_attempt",
            "input",
            {
                **request,
                "failure": {"code": "compute-error"},
            },
        )


def test_original_source_support_reference_never_relabels_a_computation_episode():
    reference = {
        "kind": "original-source",
        "admission_id": "original-admission:one",
        "source_reference": "a" * 64,
        "role": "source",
        "position": 0,
    }
    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    completion = {
        "request_id": "request:one",
        "generation": 1,
        "task_id": 1,
        "attempt": 1,
        "holder": "owner",
        "runtime_id": "runtime:one",
        "completion": {
            "outcome": "success",
            "inputs": [],
            "outputs": [],
            "implementation_revision": "implementation:one",
            "support": [reference],
        },
    }
    assert validate_native_wire("retain_data_completion_intent", "input", completion) == completion
    reference["derivation_id"] = reference["admission_id"]
    with pytest.raises(ValueError):
        validate_native_wire("retain_data_completion_intent", "input", completion)


@pytest.mark.parametrize("member", [None, "member:one"])
def test_source_set_wire_uses_existing_semantic_reference_shapes(member):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_source_sets import SourceSetEntry
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema
    from corpus_structure.semantic.data_product_reference import (
        DataProductMemberReference,
        DataProductReference,
    )

    product = DataProductReference("product:one")
    reference = product if member is None else DataProductMemberReference(product, member)
    entry = SourceSetEntry.from_semantic_source(
        reference,
        context=SubjectContext(
            "project", "subject", "source", b"{}", subject_definition="document"
        ),
    ).record()
    native = wire_contracts()["register_data_demand"]["input"]
    schema = {
        "$schema": native["$schema"],
        "$ref": "#/definitions/source_set_entry",
        "definitions": native["definitions"],
    }
    assert validate_wire_schema(schema, entry) == entry
    with pytest.raises(ValueError, match="wire violates"):
        validate_wire_schema(schema, {**entry, "reference": {**entry["reference"], "task_id": 0}})


def test_discovery_role_wire_is_optional_closed_identifier():
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema

    native = wire_contracts()["register_data_demand"]["input"]
    schema = {
        "$schema": native["$schema"],
        "$ref": "#/definitions/discovery_selection",
        "definitions": native["definitions"],
    }
    relation = {
        "producer": "discover",
        "output_role": "result",
        "target": "profile",
        "population": "selected",
    }
    assert validate_wire_schema(schema, relation) == relation
    associated = {**relation, "target_role": "source"}
    assert validate_wire_schema(schema, associated) == associated
    for value in (None, "", 1):
        with pytest.raises(ValueError, match="wire violates"):
            validate_wire_schema(schema, {**relation, "target_role": value})
    with pytest.raises(ValueError, match="wire violates"):
        validate_wire_schema(schema, {**associated, "unknown": "source"})


def _recursive_wire_examples():
    valid = [
        ["null"],
        ["known-absent"],
        ["unknown"],
        ["unavailable"],
        ["boolean", False],
        ["string", "x"],
        ["date", "2026-11-14"],
        ["datetime", "2026-11-14T12:00:00Z"],
        ["float", "0.5"],
        ["integer", "9007199254740993"],
        ["decimal", "1.25e-3"],
        ["present", ["null"]],
        ["sequence", []],
        ["ordered-bag", [["string", "x"]]],
        ["bag", [["boolean", True]]],
        ["set", [["integer", "2"]]],
        ["mapping", [["name", ["string", "x"]]]],
    ]
    nested = ["integer", "17"]
    for _ in range(16):
        nested = ["mapping", [["node", ["sequence", [nested]]]]]
    valid.append(nested)
    invalid = [
        None,
        [],
        ["unrecognized"],
        ["null", None],
        ["boolean", 1],
        ["integer", "1.2"],
        ["decimal", "NaN"],
        ["present"],
        ["sequence", [["integer", "bad"]]],
        ["mapping", [["x"]]],
        ["mapping", [[1, ["null"]]]],
        ["string", "x", "extra"],
    ]
    bad_leaf = ["integer", "not-an-integer"]
    for _ in range(16):
        bad_leaf = ["mapping", [["node", ["sequence", [bad_leaf]]]]]
    return valid, [*invalid, bad_leaf]


def _semantic_wire_schema():
    from corpus_structure.semantic.data_operation_wire import schema_closure

    definitions = wire_contracts()["retain_data_completion_intent"]["input"]["definitions"]
    return schema_closure({"$ref": "#/definitions/semantic_value"}, definitions)


def test_tagged_recursive_wire_preserves_all_variants_and_nested_refusals():
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema

    schema = _semantic_wire_schema()
    valid, invalid = _recursive_wire_examples()
    for value in valid:
        assert validate_wire_schema(schema, value) == value
    for value in invalid:
        with pytest.raises(ValueError):
            validate_wire_schema(schema, value)


@pytest.mark.db
def test_native_tagged_recursive_wire_preserves_the_same_independent_cases(infrastructure_rollback):
    from sqlalchemy import text

    schema = canonical_bytes(_semantic_wire_schema()).decode()
    infrastructure_rollback.execute(text("CREATE EXTENSION IF NOT EXISTS pg_jsonschema"))
    valid, invalid = _recursive_wire_examples()
    for expected, values in ((True, valid), (False, invalid)):
        for value in values:
            actual = infrastructure_rollback.scalar(
                text(
                    "SELECT public.json_matches_schema(CAST(:schema AS json), CAST(:value AS json))"
                ),
                {"schema": schema, "value": canonical_bytes(value).decode()},
            )
            assert actual is expected, value


@pytest.mark.parametrize("mutation", (None, "missing", "empty", "wrong-type", "extra"))
def test_read_obligation_carries_required_checked_subject_definition(mutation):
    from corpus_structure.semantic.data_operation_wire import schema_closure, validate_wire_schema

    contract = wire_contracts()["read_demand_result"]["output"]
    schema = schema_closure({"$ref": "#/definitions/result_obligation"}, contract["definitions"])
    value: dict[str, Any] = dict(
        id="obligation:actual",
        obligation_id="obligation:actual",
        demand_id="demand:actual",
        operation_id="operation:actual",
        subject="subject:actual",
        subject_definition="document",
        original_source="source:actual",
        analyzed_scope={},
        parameters={},
        historical_fate=None,
        fate="waiting",
        request_id=None,
        generation=None,
        intent_id=None,
    )
    if mutation == "missing":
        del value["subject_definition"]
    elif mutation == "empty":
        value["subject_definition"] = ""
    elif mutation == "wrong-type":
        value["subject_definition"] = 7
    elif mutation == "extra":
        value["implicit_subject_alias"] = "document"
    if mutation is None:
        assert validate_wire_schema(schema, value) == value
    else:
        with pytest.raises(ValueError):
            validate_wire_schema(schema, value)


def test_waiting_fate_retains_its_exact_read_and_refuses_a_retired_watermark():
    payload: dict[str, ExactJSONValue] = {
        "obligation_id": "obligation:waiting",
        "fate": "awaiting-inputs",
        "selection": {"reasons": [], "read_id": "read:visible-prerequisites"},
    }
    assert validate_native_wire("record_data_fate", "input", payload) == payload
    for invalid in (0, "", None):
        malformed = copy.deepcopy(payload)
        selection = malformed["selection"]
        assert isinstance(selection, dict)
        selection["read_id"] = invalid
        with pytest.raises(ValueError):
            validate_native_wire("record_data_fate", "input", malformed)
    retired = copy.deepcopy(payload)
    retired_selection = retired["selection"]
    assert isinstance(retired_selection, dict)
    retired_selection["inputs_watermark"] = "retired"
    with pytest.raises(ValueError, match="Additional properties"):
        validate_native_wire("record_data_fate", "input", retired)


def test_controlled_storage_validates_request_dependent_and_ordered_replies():
    from corpus_structure.semantic._data_operation_wire import (
        WireClaimDataRequestsRequest,
        WireRequestId,
    )
    from semantic.data_operation_binding_support import WireCheckedStorage

    payload: WireClaimDataRequestsRequest = {
        "items": [{"request_id": WireRequestId("request:one"), "generation": 1}],
        "holder": "owner",
        "lease_seconds": 3,
    }
    seen = []

    def reply(request):
        seen.append(request["items"][0]["request_id"])
        return {"items": [{"state": "no-work"}]}

    storage = WireCheckedStorage({"claim_data_requests": iter((reply, {"items": []}))})
    assert storage.claim_data_requests(payload) == {"items": [{"state": "no-work"}]}
    assert storage.claim_data_requests(payload) == {"items": []}
    assert seen == ["request:one"]
    with pytest.raises(StopIteration):
        storage.claim_data_requests(payload)
    invalid = WireCheckedStorage(
        {"claim_data_requests": lambda request: {"items": [{"state": "claimed", "result": {}}]}}
    )
    with pytest.raises(ValueError, match="native wire violates schema"):
        invalid.claim_data_requests(payload)


def test_controlled_read_page_has_required_native_fields():
    from semantic.demand_result_support import demand_result_page

    page = demand_result_page()
    assert page["obligations"][0]["operation_id"] == "op:A"
    del page["obligations"][0]["subject_definition"]
    with pytest.raises(ValueError, match="subject_definition"):
        validate_native_wire("read_demand_result", "output", page)


def test_public_result_refuses_scheduler_fields_and_private_result_admits_them():
    from semantic.demand_result_support import demand_result_page

    page = demand_result_page()
    for name, value in (
        ("native_readiness", None),
        ("native_settlement", None),
        ("binding_origin_changed", False),
        ("binding_scope_changed", False),
        ("binding_authority_changed", False),
    ):
        malformed = copy.deepcopy(page)
        malformed["obligations"][0][name] = value
        with pytest.raises(ValueError, match="Additional properties"):
            validate_native_wire("read_demand_result", "output", malformed)
    private = demand_result_page(scheduler=True)
    assert private["obligations"][0]["native_readiness"] is None
    assert private["obligations"][0]["native_settlement"] is None


def test_scoped_read_selection_has_explicit_private_intent_digest_contract():
    selection = dict(
        version="data-demand-public-selection-v1",
        model="a" * 64,
        intent_digest="native-intent:exact-digest",
        roots=[],
        targets=["structure.admit"],
        root_operations=["structure.admit"],
        discovery=[],
    )
    request = dict(
        demand_id="demand:actual", scope={"product_ids": ["product:actual"]}, selection=selection
    )
    assert validate_native_wire("read_demand_result", "input", request) == request
    for field in ("original_sources", "source_sets", "operations"):
        with pytest.raises(ValueError, match="schema"):
            validate_native_wire(
                "read_demand_result", "input", {**request, "selection": {**selection, field: {}}}
            )


def test_generated_native_format_is_advisory_while_date_model_owns_domain_check():
    from datetime import date

    from pydantic import BaseModel, ValidationError

    from corpus_structure.semantic.data_operation_wire import NativeJsonSchema, checked_json_schema
    from corpus_structure.semantic.schema_validation import prepared_schema_validator

    class DatedRecord(BaseModel):
        observed: date

    schema = DatedRecord.model_json_schema(schema_generator=NativeJsonSchema)
    assert schema["properties"]["observed"]["x-ddo-format"] == "date"
    assert "format" not in schema["properties"]["observed"]
    assert DatedRecord.model_validate_json('{"observed":"2026-11-21"}').observed == date(
        2026, 11, 21
    )
    with pytest.raises(ValidationError):
        DatedRecord.model_validate_json('{"observed":"not-a-date"}')
    # Native profile remains structural. The actual domain owner enforces dates.
    prepared_schema_validator(json.dumps(schema).encode()).validate({"observed": "not-a-date"})
    authored = {"type": "string", "format": "date"}
    assert checked_json_schema(authored) == authored
