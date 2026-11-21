"""Prepared validators for explicitly declared, locally resolved JSON Schema contracts."""

import math
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache
from typing import Any

from jsonschema.protocols import Validator
from jsonschema.validators import validator_for
from referencing import Registry, Resource

from .data_operation_json import JsonBoundaryError, native_json_loads

_DIALECTS = {
    "http://json-schema.org/draft-07/schema#",
    "https://json-schema.org/draft/2020-12/schema",
}


def _schema_numbers(value):
    """Supply mathematical JSON numbers to the library without a float round trip.

    This view is temporary validator input. Native values retain their declared
    transport and D1 identity policies when returned to the consuming boundary.
    """
    if type(value) is Decimal or type(value) is float:
        finite = value.is_finite() if type(value) is Decimal else math.isfinite(value)
        if not finite:
            raise JsonBoundaryError("JSON Schema values require finite numbers")
        number = Fraction(str(value))
        return number.numerator if number.denominator == 1 else number
    if type(value) is dict:
        updates = {}
        for key, item in value.items():
            checked = _schema_numbers(item)
            if checked is not item:
                updates[key] = checked
        return {**value, **updates} if updates else value
    if type(value) is list:
        checked = [_schema_numbers(item) for item in value]
        return (
            value
            if all(before is after for before, after in zip(value, checked, strict=True))
            else checked
        )
    return value


@dataclass(frozen=True)
class PreparedSchemaValidator:
    """One captured schema evaluator with its native numeric adapter."""

    evaluator: Validator

    def validate(self, value: Any) -> None:
        self.evaluator.validate(_schema_numbers(value))


@lru_cache(maxsize=256)
def prepared_schema_validator(
    content: bytes, resources: tuple[tuple[str, bytes], ...] = ()
) -> PreparedSchemaValidator:
    """Prepare an explicit dialect and closed captured reference context.

    Both root and resource bytes participate in the preparation cache key. The empty
    registry's retrieval policy refuses remote references rather than reading a URL.
    """
    schema = _schema_numbers(native_json_loads(content))
    if not isinstance(schema, dict) or schema.get("$schema") not in _DIALECTS:
        raise ValueError("JSON Schema requires an explicit supported dialect")
    validator = validator_for(schema)
    validator.check_schema(schema)
    captured = {}
    for uri, resource_content in resources:
        if uri in captured:
            raise ValueError("duplicate captured JSON Schema resource: " + uri)
        value = _schema_numbers(native_json_loads(resource_content))
        if not isinstance(value, dict) or value.get("$schema") not in _DIALECTS:
            raise ValueError("captured JSON Schema requires an explicit supported dialect")
        validator_for(value).check_schema(value)
        captured[uri] = Resource.from_contents(value)
    return PreparedSchemaValidator(
        validator(schema, registry=Registry().with_resources(captured.items()))
    )
