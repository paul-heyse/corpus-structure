"""Independent equivalence and refusal cases for captured wire validators."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

import pytest
from pydantic import ValidationError

from corpus_structure.semantic import _data_operation_wire as generated
from corpus_structure.semantic.demand_wire import _demand_result_adapter
from corpus_structure.semantic.demand_wire_schema import (
    UnsupportedWireSchema,
    acquire_wire_validator_runtime,
    capture_core_schema,
    capture_wire_validator,
)
from semantic.demand_result_support import demand_result_page


def test_captured_validator_preserves_native_optional_and_exact_numeric_fields():
    original = demand_result_page()
    original.pop("original_source_admissions")
    original["uses"][0]["products"][0]["analyzed_scope"] = {"amount": Decimal("12.340")}
    adapter = _demand_result_adapter()
    captured = capture_wire_validator(adapter, generated)
    actual = captured.validate_python(original)
    assert actual == adapter.validate_python(original, strict=True, extra="forbid")
    assert "original_source_admissions" not in actual
    assert (
        actual["uses"][0]["products"][0]["analyzed_scope"]["amount"].as_tuple()
        == Decimal("12.340").as_tuple()
    )


@pytest.mark.parametrize("mutation", ["extra", "integer", "literal", "array"])
def test_captured_schema_matches_independent_shape_refusals(mutation):
    source = demand_result_page()
    if mutation == "extra":
        source["uses"][0]["products"][0]["unknown"] = 1
    elif mutation == "integer":
        source["uses"][0]["products"][0]["multiplicity"] = True
    elif mutation == "literal":
        source["view"] = "foreign"
    else:
        source["uses"] = {}
    adapter = _demand_result_adapter()
    captured = capture_wire_validator(adapter, generated)
    with pytest.raises(ValidationError) as baseline:
        adapter.validate_python(source, strict=True, extra="forbid")
    with pytest.raises(ValidationError) as actual:
        captured.validate_python(source)
    assert [item["type"] for item in actual.value.errors()] == [
        item["type"] for item in baseline.value.errors()
    ]


@pytest.mark.parametrize("mutation", ["callback", "metadata", "required", "class-hook"])
def test_capture_refuses_schema_behavior_and_changed_generated_fields(mutation, monkeypatch):
    schema = cast(dict[str, Any], deepcopy(_demand_result_adapter().core_schema))
    typed = next(item for item in schema["definitions"] if item["type"] == "typed-dict")
    field = next(iter(typed["fields"].values()))
    if mutation == "callback":
        field["schema"] = {
            "type": "function-before",
            "function": {"type": "no-info", "function": lambda x: x},
            "schema": {"type": "str"},
        }
    elif mutation == "metadata":
        field["metadata"] = {"pydantic_js_functions": [lambda x: x]}
    elif mutation == "required":
        field["required"] = not field["required"]
    else:
        monkeypatch.setattr(
            typed["cls"], "__get_pydantic_core_schema__", lambda *args: {}, raising=False
        )
    if mutation in {"class-hook", "required"}:
        with pytest.raises(ValueError) as failure:
            capture_core_schema(schema, generated)
        assert not isinstance(failure.value, UnsupportedWireSchema)
    else:
        with pytest.raises(UnsupportedWireSchema):
            capture_core_schema(schema, generated)


def test_schema_reference_identity_ignores_process_object_ids():
    schema = _demand_result_adapter().core_schema
    first = capture_core_schema(schema, generated)

    def renamed(value):
        if type(value) is list:
            return [renamed(item) for item in value]
        if type(value) is dict:
            return {
                key: "other-process:" + item if key in {"ref", "schema_ref"} else renamed(item)
                for key, item in value.items()
            }
        return value

    assert capture_core_schema(renamed(schema), generated) == first


def test_live_native_binding_mutation_refuses_before_validation(monkeypatch):
    runtime = acquire_wire_validator_runtime()
    monkeypatch.setattr(runtime.public, "SchemaValidator", object)
    with pytest.raises(ValueError, match="constructor binding changed"):
        runtime.check()


def test_changed_native_method_and_schema_witness_refuse(monkeypatch):
    captured = capture_wire_validator(_demand_result_adapter(), generated)
    monkeypatch.setattr(captured.runtime.constructor, "validate_python", lambda *args, **kw: {})
    with pytest.raises(ValueError, match="native class changed"):
        captured.validate_python({})
    monkeypatch.undo()
    with pytest.raises(ValueError, match="schema differs"):
        replace(captured, schema=b"{}").check()
