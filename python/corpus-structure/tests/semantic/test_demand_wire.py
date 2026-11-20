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


def test_typed_decode_refuses_library_retagging_even_when_json_spelling_is_equal(monkeypatch):
    from corpus_structure.semantic import demand_wire

    class RetaggingAdapter:
        def validate_python(self, source, **options):
            # A future library/schema change must not convert exact scope numbers.
            import copy

            result = copy.deepcopy(source)
            result["uses"][0]["products"][0]["analyzed_scope"] = {"scale": 1.2}
            return result

    source = demand_result_page()
    source["uses"][0]["products"][0]["analyzed_scope"] = {"scale": Decimal("1.2")}
    monkeypatch.setattr(demand_wire, "_demand_result_adapter", RetaggingAdapter)
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
        type(None), bool, int, float, Decimal, str, dict,
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


def test_projection_snapshot_refuses_changed_values_and_arbitrary_objects():
    from dataclasses import replace

    from corpus_structure.semantic.demand_queries import DemandQueryRequest
    from corpus_structure.semantic.demand_query_projection import (
        prepare_demand_projection_inputs,
        selected_query_rows,
    )

    def prepared():
        return prepare_demand_projection_inputs(
            json_bytes(demand_result_page()),
            json_bytes(DemandQueryRequest(demand_id="demand:A", project_id="project:A").selection()),
            decimal_fixed_point_digits=100,
        )

    changed = prepared()
    changed.page["uses"][0]["products"][0]["multiplicity"] = 99
    with pytest.raises(ValueError, match="changed after their keyed acquisition"):
        list(selected_query_rows(changed))
    with pytest.raises(TypeError, match="exact inert"):
        list(selected_query_rows(replace(prepared(), page=cast(Any, object()))))
    with pytest.raises(TypeError, match="immutable material witnesses"):
        list(selected_query_rows(replace(prepared(), native_witness=cast(Any, bytearray(b"{}")))))
