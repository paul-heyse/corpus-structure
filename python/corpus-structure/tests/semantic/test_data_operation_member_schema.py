"""Independent nominal packet-variant preservation at native schema projection."""

import copy

import pytest
from jsonschema import Draft202012Validator

from corpus_structure.semantic.data_operation_storage import _member_schema


def schema():
    header = dict(member_id={"type": "string"}, kind_contract={"type": "string"}, context={"type": "object"})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {
        "Left": {"type": "object", "properties": {**header, "body": {"$ref": "#/$defs/LeftBody"}}},
        "Right": {"type": "object", "properties": {**header, "body": {"$ref": "#/$defs/RightBody"}}},
        "LeftBody": {"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"], "additionalProperties": False},
        "RightBody": {"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"], "additionalProperties": False},
    }, "type": "object", "properties": {"members": {"anyOf": [{"type": "null"}, {"type": "array", "items": {"oneOf": [{"$ref": "#/$defs/Left"}, {"$ref": "#/$defs/Right"}]}}]}}}


def test_nominal_packet_variants_preserve_each_body_and_closed_references():
    result = _member_schema(schema())
    validator = Draft202012Validator(result)
    assert validator.is_valid({"label": "original"})
    assert validator.is_valid({"count": 2})
    assert not validator.is_valid({"count": "2"})
    assert not validator.is_valid({"label": "original", "count": 2})
    assert not validator.is_valid({"unknown": True})


@pytest.mark.parametrize("header", ["member_id", "kind_contract", "context", "body"])
def test_one_incomplete_variant_cannot_be_hidden_by_other_valid_packet(header):
    value = copy.deepcopy(schema())
    del value["$defs"]["Right"]["properties"][header]
    assert _member_schema(value) == {"not": {}}


def test_member_body_does_not_gain_schema_from_non_packet_collections():
    assert _member_schema({"properties": {"members": {"type": "array", "items": {"type": "string"}}}}) == {"not": {}}
