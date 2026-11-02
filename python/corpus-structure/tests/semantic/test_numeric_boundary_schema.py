"""Numeric constraints remain numeric metadata through JSON-serving boundaries."""

import json
from decimal import Decimal

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release


def test_numeric_representation_bounds_and_exact_decimal_are_preserved():
    source = SourceArtifact(
        "numeric",
        b"""id: https://example.org/numeric
name: numeric
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types:
 integer: {base: int}
 float: {base: float}
 decimal: {base: Decimal}
classes:
 Numbers:
  attributes:
   count: {range: integer, minimum_value: 1.5, maximum_value: 3.5, required: true}
   score: {range: float, minimum_value: 0.1, maximum_value: 0.9, required: true}
   exact: {range: decimal, minimum_value: 0.1, required: true}
""",
    )
    release = prepare_release(SourceBundle(source.name, (source,)))
    for mode in ("validation", "serialization"):
        schema = release.json_schema("Numbers", mode=mode)
        Draft202012Validator.check_schema(json.loads(json.dumps(schema)))
        fields = schema["properties"]
        assert isinstance(fields, dict)
        assert fields["count"]["minimum"] == 2
        assert fields["count"]["maximum"] == 3
        assert type(fields["score"]["minimum"]) is float
    good = release.validate_json(
        "Numbers", '{"count":2,"score":0.1,"exact":"0.100000000000000001"}'
    )
    assert good.model_dump()["exact"] == Decimal("0.100000000000000001")
    for value in (
        '{"count":1,"score":0.1,"exact":"0.1"}',
        '{"count":4,"score":0.1,"exact":"0.1"}',
        '{"count":2,"score":0.01,"exact":"0.1"}',
        '{"count":2,"score":0.1,"exact":"0.01"}',
    ):
        with pytest.raises(ValidationError):
            release.validate_json("Numbers", value)
