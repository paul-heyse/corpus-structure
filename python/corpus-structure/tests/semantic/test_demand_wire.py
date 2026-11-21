"""Generated demand field fidelity and refusing detached decode controls."""

from decimal import Decimal
from typing import Any, cast

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_wire import decode_wire_demand_result
from semantic.demand_result_support import demand_result_page


def test_generated_demand_decode_preserves_optional_fields_numbers_and_tagged_values():
    source = demand_result_page()
    source.pop("original_source_admissions")
    source["uses"][0]["products"][0]["analyzed_scope"] = {"scale": Decimal("1.20")}
    content = json_bytes(source)
    result = decode_wire_demand_result(content)
    assert json_bytes(result) == content
    assert result["uses"][0]["products"][0]["body"] == source["uses"][0]["products"][0]["body"]
    assert "attempt_failures" not in result
    assert "original_source_admissions" not in result
    assert result["uses"][0]["products"][0]["analyzed_scope"] == {"scale": Decimal("1.2")}
    result["uses"].clear()
    assert decode_wire_demand_result(content)["uses"]


def test_execution_delivery_projects_native_scope_and_ordinary_body_separately():
    from corpus_structure.orchestrate.data_operations import DemandAdvance
    from corpus_structure.orchestrate.source_reporting import native_demand_result

    source = demand_result_page()
    product = source["uses"][0]["products"][0]
    fraction = Decimal("0.123456789012345678901234")
    product["analyzed_scope"] = {"scale": fraction}
    product["body"] = {"analyzed_scope": {"scale": fraction}}
    receipt = {
        "derivation_id": "derivation:one",
        "receipt_id": "receipt:one",
        "replayed": False,
        "trust_snapshot": {"source:one": 9},
    }
    report = native_demand_result(
        DemandAdvance(source["demand_id"], json_bytes(source), (json_bytes(receipt),), 1)
    )
    delivered = report["snapshot"]["uses"][0]["products"][0]
    assert delivered["analyzed_scope"] == {"scale": fraction}
    assert delivered["body"]["analyzed_scope"]["scale"] == 0.12345678901234568
    assert report["receipts"] == [receipt]


@pytest.mark.parametrize("mutation", ["extra", "wrong-list", "wrong-integer", "wrong-literal"])
def test_generated_demand_decode_refuses_shape_and_unknown_keys(mutation):
    source = demand_result_page()
    if mutation == "extra":
        source["uses"][0]["products"][0]["unmodeled"] = "present"
    elif mutation == "wrong-list":
        source["uses"] = {}
    elif mutation == "wrong-integer":
        source["uses"][0]["products"][0]["multiplicity"] = True
    else:
        source["view"] = "unmodeled"
    with pytest.raises(ValidationError):
        decode_wire_demand_result(json_bytes(source))


def test_generated_demand_decode_refuses_mutable_or_user_defined_input():
    class Bytes(bytes):
        pass

    for value in (bytearray(b"{}"), Bytes(b"{}"), {}):
        with pytest.raises(TypeError, match="exact immutable bytes"):
            decode_wire_demand_result(cast(Any, value))


@pytest.mark.parametrize(
    ("field", "original", "changed"),
    [
        ("analyzed_scope", {"scale": Decimal("1.2")}, {"scale": 1.2}),
        ("analyzed_scope", {"scale": Decimal("1.20")}, {"scale": Decimal("1.2")}),
        ("body", {"number": -0.0}, {"number": 0.0}),
    ],
)
def test_typed_decode_refuses_changes_to_exact_material(monkeypatch, field, original, changed):
    from corpus_structure.semantic import demand_wire

    class RetaggingAdapter:
        def validate_python(self, source, **options):
            source["uses"][0]["products"][0][field] = changed
            return source

    source = demand_result_page()
    source["uses"][0]["products"][0][field] = original
    monkeypatch.setattr(demand_wire, "captured_demand_wire_validator", RetaggingAdapter)
    with pytest.raises(ValueError, match="changed its material native record"):
        decode_wire_demand_result(json_bytes(source))


def test_owned_json_copy_detaches_nested_values_and_preserves_exact_scalar_types():
    from corpus_structure.semantic.data_operation_json import own_json_value

    nested = {"nested": []}
    original = {"values": [None, True, 7, 1.25, Decimal("1.250"), "text", nested]}
    copied = own_json_value(original)
    assert copied == original
    assert copied is not original and copied["values"] is not original["values"]
    assert [type(value) for value in copied["values"]] == [
        type(None),
        bool,
        int,
        float,
        Decimal,
        str,
        dict,
    ]
    copied["values"][-1]["nested"].append("new")
    assert nested["nested"] == []


def test_owned_json_copy_refuses_subclasses_and_protocols_without_calling_them():
    from corpus_structure.semantic.data_operation_json import own_json_value

    calls = []

    class Dictionary(dict):
        def __iter__(self):
            calls.append("iter")
            return super().__iter__()

    class Scalar:
        def __float__(self):
            calls.append("float")
            return 1.0

    class Text(str):
        def __str__(self):
            calls.append("str")
            return super().__str__()

    for value in (Dictionary(a=7), Scalar(), Text("a"), {7: "wrong-key"}):
        with pytest.raises(TypeError, match="owned JSON"):
            own_json_value(value)
    assert not calls
    for value in (float("inf"), Decimal("NaN")):
        with pytest.raises(ValueError, match="finite"):
            own_json_value(value)


def test_projection_snapshot_owns_nested_values_and_refuses_arbitrary_objects():
    from dataclasses import replace

    from corpus_structure.semantic.demand_queries import DemandQueryRequest
    from corpus_structure.semantic.demand_query_projection import (
        prepare_demand_projection_inputs,
        selected_query_rows,
    )
    from corpus_structure.semantic.owned_json import FrozenObject, freeze_json, thaw_json

    def prepared():
        return prepare_demand_projection_inputs(
            json_bytes(demand_result_page()),
            json_bytes(
                DemandQueryRequest(demand_id="demand:A", project_id="project:A").selection()
            ),
            decimal_fixed_point_digits=100,
        )

    original = {"fields": [Decimal("12.340"), -0.0]}
    frozen = freeze_json(original)
    original["fields"].clear()
    assert str(thaw_json(frozen)) == "{'fields': [Decimal('12.340'), -0.0]}"
    inputs = prepared()
    rows = list(selected_query_rows(inputs))
    rows[0]["meaning_body"].clear()
    assert next(selected_query_rows(inputs))["meaning_body"]
    with pytest.raises(TypeError, match="exact inert"):
        list(selected_query_rows(replace(inputs, page=cast(Any, object()))))
    with pytest.raises(TypeError, match="immutable object fields"):
        list(selected_query_rows(replace(inputs, page=FrozenObject(cast(Any, [])))))


def test_member_meaning_retains_the_original_tagged_subtree_and_decimal_fidelity():
    from corpus_structure.semantic.demand_results import DemandResult

    content = json_bytes(demand_result_page())
    rows = DemandResult(content).members()
    assert rows[1]["meaning_body"] == ["mapping", [["amount", ["decimal", "12.34"]]]]
    assert type(rows[1]["body"]["amount"]) is Decimal
    assert str(rows[1]["body"]["amount"]) == "12.34"
    assert rows[2]["meaning_body"] == [
        "mapping",
        [["direction", ["string", "outgoing"]], ["target", ["string", "first"]]],
    ]
    selected = DemandResult(json_bytes(demand_result_page(member_id="second"))).members()
    assert selected[0]["meaning_body"] == rows[2]["meaning_body"]
    original_container = json_bytes(rows[0]["meaning_body"])
    rows[1]["meaning_body"][1].clear()
    assert json_bytes(rows[0]["meaning_body"]) == original_container


@pytest.mark.parametrize(
    "malformation", ["noncanonical-decimal", "missing-body", "non-record-packet"]
)
def test_member_original_pairing_refuses_malformed_source(malformation):
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.demand_results import DemandResult

    source = demand_result_page()
    packet = dict(
        member_id="first",
        kind_contract="kind:first",
        context=dict(
            subject="one", subject_definition="document", original_source=None, analyzed_scope={}
        ),
        body={"amount": Decimal("12.34")},
    )
    if malformation == "missing-body":
        packet.pop("body")
    body = dict(members=[7] if malformation == "non-record-packet" else [packet])
    source["uses"][0]["products"][0]["body"] = semantic_value(body)
    content = json_bytes(source)
    if malformation == "noncanonical-decimal":
        content = content.replace(b'"12.34"', b'"12.340"')
    with pytest.raises((ValueError, TypeError, KeyError)):
        DemandResult(content).members()
