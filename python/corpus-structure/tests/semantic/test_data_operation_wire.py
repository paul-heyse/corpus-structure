"""Independent closed-wire types and their effective model correspondence."""

from __future__ import annotations

import copy
import json
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
from semantic.data_operation_port_support import captured


def wire_model(sources=None, binding=None):
    declaration: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
    declaration["id"] = "data.claim_data_request"
    declaration["roles"][0].update(
        name="request",
        parameter="payload",
        kind=wire_role_kind("claim_data_request", "input", sources),
    )
    declaration["roles"][1].update(
        name="result",
        parameter="payload",
        kind=wire_role_kind("claim_data_request", "output", sources),
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
            "claim_data_request",
            "input",
            {"request_id": "request:x", "holder": "worker", "lease_seconds": lease},
        )


def test_exact_wire_fields_and_result_variants_are_explicit():
    payload = {"request_id": "request:x", "holder": "worker", "lease_seconds": 3}
    assert validate_native_wire("claim_data_request", "input", payload) == payload
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_request", "input", {**payload, "extra": 2})
    assert validate_native_wire("claim_data_request", "output", {"state": "no-work"}) == {
        "state": "no-work"
    }
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_request", "output", {"state": "claimed"})
    with pytest.raises(ValueError):
        validate_native_wire("claim_data_request", "output", {"state": "no-work", "task_id": 4})


def test_shared_wire_contract_is_detached_and_has_only_local_resolved_references():
    contracts = wire_contracts(captured())
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

    from corpus_structure.semantic.contracts import (
        OperationCallBinding,
        OperationFieldBinding,
        OperationFieldType,
    )
    from corpus_structure.semantic.data_operation_artifacts import compile_data_operation_artifacts

    model = wire_model(captured())
    scalar_json = OperationFieldType("json_payload", False, False)
    parameter = OperationFieldBinding(
        "payload", "native-wire", False, native_parameter="p_payload", resolved=scalar_json
    )
    result = OperationFieldBinding(
        "payload", "native-wire", False, native_field="payload", resolved=scalar_json
    )
    call = OperationCallBinding(
        "claim_data_request",
        "ops.claim_data_request",
        (parameter,),
        result_class="ClaimDataRequestResult",
        result_fields=(result,),
        cardinality="one",
        ordered=False,
        source_digest="wire-test",
        result_mode="json",
    )
    artifact = compile_data_operation_artifacts(
        model, (("data.claim_data_request", call),), native_source_digest="wire-test"
    )
    module = ModuleType("corpus_structure.semantic._test_captured_wire")
    module.__package__ = "corpus_structure.semantic"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(artifact.calls, "captured_wire.py", "exec"), module.__dict__)
    request = module.__dict__["_claim_data_requestRequest"]
    result_type = module.__dict__["ClaimDataRequestResult"]
    checked = request.model_validate_json(
        '{"payload":{"request_id":"request:x","holder":"worker","lease_seconds":3}}', strict=True
    )
    assert checked.payload["lease_seconds"] == 3
    with pytest.raises(ValidationError):
        request.model_validate_json(
            '{"payload":{"request_id":"request:x","holder":"worker","lease_seconds":"3"}}',
            strict=True,
        )
    assert result_type.model_validate_json(
        '{"payload":{"state":"no-work"}}', strict=True
    ).payload == {"state": "no-work"}
    with pytest.raises(ValidationError):
        result_type.model_validate_json('{"payload":{"state":"claimed"}}', strict=True)


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
            "context": {"subject": "member:m", "original_source": "source:x", "analyzed_scope": {}},
            "body": ["mapping", []],
            "choices": [{"choice_group": "g", "alternative": "a", "selected": True}],
        }
    ]
    assert validate_native_wire("retain_data_completion_intent", "input", invalid)
    invalid["completion"]["outputs"][0]["product"]["members"][0]["choices"][0]["selected"] = "true"
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
    owner = KIND_PREFIX + "claim_data_request_request"

    def fingerprint(model):
        return next(i.key for i in model.identities if i.owner == owner and i.domain == "kind")

    assert fingerprint(before) == fingerprint(after)


@pytest.mark.parametrize("field,invalid,valid", [("lease_seconds", 0, 3), ("holder", "", "worker")])
def test_wire_predicate_literals_reuse_the_exact_constrained_field_authority(field, invalid, valid):
    from corpus_structure.semantic.types import PreparationError

    owner = KIND_PREFIX + "claim_data_request_request"
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
        "version": "data-demand-intent-v1",
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
        validate_native_wire("attach_data_request", "input", request)
    binding["read_id"] = "read:x"
    assert (
        validate_native_wire("attach_data_request", "input", request)["binding"]["read_id"]
        == "read:x"
    )


def member_completion(member, *, domain_body=None):
    from corpus_structure.semantic.data_operation_identity import semantic_value

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
    "endpoint,valid",
    [
        ({"scope": "local", "role": "object", "member_id": "member:other"}, True),
        (
            {
                "scope": "external",
                "role": "object",
                "member_id": "member:other",
                "product_id": "product:other",
            },
            True,
        ),
        ({"role": "object", "member_id": "member:other"}, False),
        (
            {"scope": "local", "role": "object", "member_id": "member:other", "product_id": None},
            False,
        ),
        (
            {
                "scope": "local",
                "role": "object",
                "member_id": "member:other",
                "product_id": "product:self",
            },
            False,
        ),
        ({"scope": "external", "role": "object", "member_id": "member:other"}, False),
    ],
)
def test_endpoint_scope_is_explicit_and_local_never_embeds_a_self_product_key(endpoint, valid):
    member = {
        "member_id": "member:x",
        "kind_contract": "kind:member",
        "context": {"subject": "occurrence:x", "original_source": "source:x", "analyzed_scope": {}},
        "body": ["mapping", [["endpoints", ["sequence", []]]]],
        "endpoints": [endpoint],
    }
    from corpus_structure.semantic.data_operation_identity import semantic_value

    member["body"] = semantic_value({"endpoints": [endpoint]})
    if valid:
        assert validate_native_wire(
            "retain_data_completion_intent",
            "input",
            member_completion(member, domain_body={"endpoints": [endpoint]}),
        )
    else:
        with pytest.raises(ValueError):
            validate_native_wire(
                "retain_data_completion_intent", "input", member_completion(member)
            )


def test_member_context_and_endpoint_discriminator_remain_typed_in_effective_fields():
    model = wire_model(captured())
    context = next(
        k for k in model.kinds if k.semantic_id == KIND_PREFIX + "product_member/property/context"
    )
    assert json.loads(context.facts)["required"] is True
    assert json.loads(context.facts)["range"] == KIND_PREFIX + "member_context"
    scope = next(k for k in model.kinds if k.semantic_id == KIND_PREFIX + "endpoint/property/scope")
    assert json.loads(scope.facts)["range"] == "primitive:string"


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
        "context": {"subject": "occurrence:x", "original_source": "source:x", "analyzed_scope": {}},
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
    declaration: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
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
    }
    result = {
        "population_id": "population:selected",
        "name": "selected-items",
        "semantic_key": "population-value:one",
        "members": [],
        "complete": True,
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
        reference, context=SubjectContext("project", "subject", "source", b"{}")
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
