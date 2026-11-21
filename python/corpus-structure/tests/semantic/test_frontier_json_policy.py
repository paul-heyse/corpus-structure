"""Independent native-frontier numeric roles, custody and captured-call controls."""

import json
import sys
from decimal import Decimal
from hashlib import sha256
from types import ModuleType
from typing import Any, cast

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes, native_json_loads
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.data_operation_wire import (
    validate_native_wire,
    wire_contract_digest,
    wire_contracts,
    wire_nominal_correspondence,
)
from corpus_structure.semantic.demand_results import _PIN_FIELDS, CutSelection, DemandResult
from corpus_structure.semantic.demand_wire import (
    decode_wire_demand_request,
    decode_wire_demand_result,
)
from semantic.demand_result_support import demand_result_page


def frontier():
    value = demand_result_page()
    value["view"] = "frontier"
    value["support_page"] = None
    for use in value["uses"]:
        for product in use["products"]:
            product.pop("body", None)
            product["body_state"] = "not_requested"
    value["selection"]["roots"] = [
        {"subject": "root", "original_source": "source:A", "analyzed_scope": {
            "fraction": Decimal("0.12345678901234567890123456789"),
            "whole": Decimal("9007199254740993.0"),
            "analyzed_scope": {"fraction": Decimal("1.20")},
        }}
    ]
    value["selection"]["operations"][0]["parameters"] = {
        "ordinary": {"analyzed_scope": {"fraction": Decimal("0.12345678901234567890123456789")}}
    }
    return value


def expect_roles(value):
    root = value["selection"]["roots"][0]["analyzed_scope"]
    assert type(root["fraction"]) is Decimal
    assert root["fraction"].as_tuple() == Decimal("0.12345678901234567890123456789").as_tuple()
    assert root["whole"].as_tuple() == Decimal("9007199254740993.0").as_tuple()
    assert root["analyzed_scope"]["fraction"].as_tuple() == Decimal("1.20").as_tuple()
    ordinary = value["selection"]["operations"][0]["parameters"]["ordinary"]["analyzed_scope"]
    assert type(ordinary["fraction"]) is float
    assert ordinary == {"fraction": 0.12345678901234568}


def test_frontier_raw_admission_then_declared_projection_and_owned_decode():
    content = json_bytes(frontier())
    admitted = validate_native_wire("read_demand_result", "output", native_json_loads(content))
    expect_roles(admitted)
    decoded = decode_wire_demand_result(content)
    expect_roles(decoded)
    decoded["selection"]["roots"].clear()
    expect_roles(decode_wire_demand_result(content))
    page = DemandResult(content)
    assert page.content is content
    expect_roles(page.record)
    expect_roles(page.cut.record)


def test_frontier_cut_identity_retains_existing_d1_bytes():
    value = frontier()
    value["selection"]["operations"][0]["parameters"] = {}
    cut_bytes = json_bytes({name: value[name] for name in _PIN_FIELDS})
    cut = CutSelection(cut_bytes)
    assert cut.content is cut_bytes
    assert cut.identity == "cut-selection:" + sha256(cut_bytes).hexdigest()
    assert json_bytes(cut.record) == cut_bytes
    assert DemandResult(json_bytes(value)).cut.content == cut_bytes


def test_frontier_continuation_keeps_context_and_ordinary_parameter_meanings():
    value = frontier()
    value["continuation"] = {
        "demand_id": value["demand_id"], "selection": value["selection"],
        "trust_snapshot": {}, "after": "obligation:A", "limit": 1, "max_bytes": 8192,
        "read_id": value["read_id"], "read_snapshot": value["read_snapshot"],
        "frontier_at": value["frontier_at"], "view": "frontier", "scope": {},
    }
    page = DemandResult(json_bytes(value))
    continuation = page.continuation
    expect_roles(continuation)
    expect_roles(decode_wire_demand_request(json_bytes(continuation)))


@pytest.mark.parametrize("token", ["1.00000000000000000000001", "true"])
def test_frontier_integer_constraints_see_exact_tokens_before_projection(token):
    request = '{"demand_id":"demand:A","view":"frontier","limit":' + token + '}'
    with pytest.raises(ValueError, match="schema"):
        decode_wire_demand_request(request.encode())
    assert decode_wire_demand_request(b'{"demand_id":"demand:A","view":"frontier","limit":1.0}')["limit"] == 1


def test_frontier_refuses_dynamic_support_page_in_declared_slice():
    value = frontier()
    value["support_page"] = {"records": [], "after": None, "complete": True}
    with pytest.raises(ValueError, match="absent support page"):
        validate_native_wire("read_demand_result", "output", value)


def test_ambient_storage_and_compact_context_retain_native_number_tokens():
    value = frontier()
    encoded = json_bytes({"payload": value, "contract_digest": wire_contract_digest()}).decode()

    class Connection:
        def scalar(self, statement, parameters):
            return encoded

    storage = DataOperationStorage(cast(Any, Connection()))
    expect_roles(storage.read_demand_result(cast(Any, {"demand_id": "demand:A", "view": "frontier"})))
    compact = {name: value[name] for name in ("demand_id", "selection", "trust_snapshot", "read_id", "read_snapshot", "frontier_at")}
    encoded = json_bytes(compact).decode()
    expect_roles(storage.acquire_data_read_context("demand:A", "read:A", {}))


def test_captured_generated_frontier_call_freezes_sidecar_policy(monkeypatch):
    from corpus_structure.semantic import data_operation_wire as wire
    from corpus_structure.semantic.native_call_contracts import (
        OperationCallBinding,
        OperationFieldBinding,
        OperationFieldType,
    )
    from corpus_structure.semantic.native_call_generation import render_call_bindings

    schemas = wire_contracts()["read_demand_result"]
    scalar = OperationFieldType("json_payload", False, False)
    fields = [OperationFieldBinding("payload", "native-wire", False, resolved=scalar, wire_schema=json.dumps(schemas[direction]), wire_nominals=wire_nominal_correspondence()) for direction in ("input", "output")]
    call = OperationCallBinding("read_demand_result", "ops.read_demand_result", (fields[0],), result_class="ReadDemandResultResult", result_fields=(fields[1],), cardinality="one", ordered=False, result_mode="json", wire_contract_digest=wire_contract_digest())
    source = render_call_bindings((("data.read_demand_result", call),), identifiers_module=".identifiers")
    module = ModuleType("corpus_structure.semantic._controlled_frontier_call")
    module.__package__ = "corpus_structure.semantic"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(source, "captured_frontier.py", "exec"), module.__dict__)

    def unavailable(*args, **kwargs):
        raise AssertionError("captured call consulted ambient field-role correspondence")

    value = frontier()
    monkeypatch.setattr(wire, "wire_contextual_fields", unavailable)
    encoded = json_bytes({"payload": value, "contract_digest": wire_contract_digest()}).decode()

    class Connection:
        def scalar(self, statement):
            return encoded

    expect_roles(module.read_demand_result(cast(Any, Connection()), payload={"demand_id": "demand:A", "view": "frontier"})["payload"])


def test_historical_frontier_and_manifest_keep_original_cut_identity():
    from corpus_structure.serve.demand_export_manifest import decode_export_manifest
    from semantic.test_demand_export_manifest import manifest

    value = frontier()
    original = CutSelection.from_native(value)
    page = DemandResult(json_bytes(value))
    expect_roles(page.record)
    assert page.cut.identity == original.identity
    assert page.cut.content == original.content
    source = manifest()
    source["cut"] = native_json_loads(original.content)
    source["cut_id"] = original.identity
    encoded = json_bytes(source)
    checked = decode_export_manifest(encoded)
    assert json_bytes(checked.model_dump(mode="python")) == encoded
    cut = CutSelection(json_bytes(checked.cut))
    assert cut.identity == original.identity
    expect_roles(cut.record)


@pytest.mark.parametrize("kind", ["ordinary", "contextual"])
def test_ambiguous_object_union_selects_its_actual_nested_field_role(kind):
    from corpus_structure.semantic.data_operation_wire import prepare_wire_schema

    def branch(tag):
        return {"type": "object", "properties": {"packet": {
            "type": "object", "properties": {"kind": {"const": tag}, "value": {"$ref": "#/definitions/json_value"}},
            "required": ["kind", "value"], "additionalProperties": False,
        }}, "required": ["packet"], "additionalProperties": False}

    schema = {"oneOf": [{"$ref": "#/definitions/contextual"}, {"$ref": "#/definitions/ordinary"}],
              "definitions": {"contextual": branch("contextual"), "ordinary": branch("ordinary"),
                              "json_value": {"type": ["object", "array", "number", "string", "boolean", "null"]}}}
    validate = prepare_wire_schema(schema, contextual_fields=("#/definitions/contextual/properties/packet/properties/value",))
    value = validate(native_json_loads(json_bytes({"packet": {"kind": kind, "value": {"analyzed_scope": Decimal("1.20")}}})))
    number = value["packet"]["value"]["analyzed_scope"]
    assert type(number) is (Decimal if kind == "contextual" else float)
    assert number == (Decimal("1.20") if kind == "contextual" else 1.2)


def test_ambient_field_roles_are_prepared_once_per_current_model(monkeypatch):
    from corpus_structure.caches import clear
    from corpus_structure.model.compiled import model_request_scope
    from corpus_structure.semantic import data_operation_wire as wire

    value = frontier()
    clear("model_entries")
    with model_request_scope():
        assert wire.wire_contextual_fields()

        def unavailable(*args, **kwargs):
            raise AssertionError("frontier call reread field correspondence")

        monkeypatch.setattr(wire, "_wire_correspondence_document", unavailable)
        for _ in range(2):
            expect_roles(wire.validate_native_wire("read_demand_result", "output", value))


@pytest.mark.parametrize("number", [1e-5, 1e20, -0.0])
def test_historical_ordinary_exponent_tokens_keep_page_and_v3_manifest_cut_ids(number):
    from corpus_structure.serve.demand_export_manifest import decode_export_manifest
    from semantic.test_demand_export_manifest import manifest

    value = frontier()
    value["selection"]["operations"][0]["parameters"] = {"ordinary": number}
    original = CutSelection.from_native(value)
    page = DemandResult(json_bytes(value))
    assert page.cut.content == original.content
    assert page.cut.identity == original.identity
    source = manifest()
    source["cut"] = {name: value[name] for name in _PIN_FIELDS}
    source["cut_id"] = original.identity
    encoded = json_bytes(source)
    checked = decode_export_manifest(encoded)
    assert json_bytes(checked.model_dump(mode="python")) == encoded
    assert CutSelection(json_bytes(checked.cut)).identity == original.identity


@pytest.mark.parametrize("explicit_view", [False, True])
def test_native_frontier_request_default_uses_the_same_declared_context_roles(explicit_view):
    value = frontier()
    request = {"demand_id": value["demand_id"], "selection": value["selection"]}
    if explicit_view:
        request["view"] = "frontier"
    expect_roles(decode_wire_demand_request(json_bytes(request)))
