"""Relation roles and captured export shapes remain independent of ambient metadata."""

from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from typing import Any

import pytest
from jsonschema.exceptions import ValidationError

from corpus_structure.semantic.data_operation_json import json_bytes, native_json_loads
from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
from corpus_structure.semantic.selected_support_contract import SelectedSupportReader


def test_request_scope_and_product_body_use_distinct_declared_roles(tmp_path):
    request = {
        "key": "request:A",
        "relation": "ops.data_request",
        "record": {"id": "A", "analyzed_scope": {"scale": Decimal("0.123456789012345678901")}},
    }
    product = {
        "key": "product:A",
        "relation": "kb.data_product",
        "record": {
            "id": "P",
            "analyzed_scope": {"scale": Decimal("0.123456789012345678901")},
            "canonical_body": {"analyzed_scope": Decimal("0.125")},
        },
    }
    index = SelectedRecordIndex(tmp_path / "support.sqlite")
    try:
        for row in (request, product):
            index.append(json_bytes(row))
        assert index.mapping("ops.data_request", ("id",))["A"]["analyzed_scope"][
            "scale"
        ] == Decimal("0.123456789012345678901")
        body = index.mapping("kb.data_product", ("id",))["P"]
        assert body["analyzed_scope"]["scale"] == Decimal("0.123456789012345678901")
        assert type(body["canonical_body"]["analyzed_scope"]) is float
        assert body["canonical_body"]["analyzed_scope"] == 0.125
        assert tuple(index.records())[1]["record"]["id"] == "A"
    finally:
        index.close()


def test_captured_shape_survives_ambient_change_and_refuses_unknown_contract(monkeypatch):
    from corpus_structure.semantic import selected_support_contract as owner

    captured = SelectedSupportReader().capture(["ops.data_request"])
    historical = SelectedSupportReader(captured)
    properties = captured["ops.data_request"]["schema"]["properties"]
    record: dict[str, Any] = {
        name: None if "anyOf" in schema else "value" for name, schema in properties.items()
    }
    record["analyzed_scope"] = {"scale": Decimal("1.234567890123456789")}
    row = {"key": "request:A", "relation": "ops.data_request", "record": record}
    payload = json_bytes(row)
    expected_digest = sha256(payload).digest()
    monkeypatch.setattr(
        owner, "ambient_support_contract", lambda _: pytest.fail("ambient schema read")
    )
    assert historical.loads(payload)["record"]["analyzed_scope"]["scale"] == Decimal(
        "1.234567890123456789"
    )
    assert sha256(payload).digest() == expected_digest
    changed = deepcopy(row)
    changed["record"]["future_column"] = "added"
    with pytest.raises(ValidationError):
        historical.record(changed)
    with pytest.raises(ValueError, match="unsupported captured support relation"):
        historical.loads(b'{"key":"x","relation":"unknown","record":{}}')


def test_support_integer_coordinate_is_checked_before_projection():
    reader = SelectedSupportReader()
    captured = reader.capture(["ops.data_derivation_output"])
    schema = captured["ops.data_derivation_output"]["schema"]
    # This small captured fixture isolates a physical integer coordinate, with
    # independent expectations for its mathematical value and refusal boundary.
    schema["properties"] = {"position": {"type": "integer"}}
    schema["required"] = ["position"]
    owned = SelectedSupportReader(captured)
    row = native_json_loads(
        b'{"key":"x","relation":"ops.data_derivation_output","record":{"position":3.0}}'
    )
    assert owned.record(row)["record"]["position"] == 3
    row["record"]["position"] = Decimal("3.125")
    with pytest.raises(ValidationError):
        owned.record(row)


def test_captured_kind_selects_body_numbers_and_unknown_kind_refuses():
    captured = SelectedSupportReader().capture(["kb.data_product"])
    # A captured structural row isolates the body role while the nominal contract
    # independently states which numeric field is an integer coordinate.
    schema = captured["kb.data_product"]["schema"]
    schema["properties"] = {"kind_contract": {"type": "string"}, "canonical_body": {}}
    schema["required"] = list(schema["properties"])
    kinds = {
        "kind:A": {
            "meaning_schema": {
                "type": "object",
                "properties": {"count": {"type": "integer"}, "analyzed_scope": {}},
                "required": ["count", "analyzed_scope"],
                "additionalProperties": False,
            }
        }
    }
    reader = SelectedSupportReader(captured, kinds=kinds)
    payload = b'{"key":"product:A","relation":"kb.data_product","record":{"kind_contract":"kind:A","canonical_body":{"count":3.0,"analyzed_scope":0.125}}}'
    row = reader.loads(payload)
    assert type(row["record"]["canonical_body"]["count"]) is int
    assert row["record"]["canonical_body"]["count"] == 3
    assert type(row["record"]["canonical_body"]["analyzed_scope"]) is float
    with pytest.raises(ValueError, match="unsupported captured support kind"):
        reader.loads(payload.replace(b"kind:A", b"kind:B"))
