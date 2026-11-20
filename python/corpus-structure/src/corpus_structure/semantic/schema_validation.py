"""Prepared validators for explicitly declared, locally resolved JSON Schema contracts."""

from functools import lru_cache

from jsonschema import Draft7Validator, Draft202012Validator
from jsonschema.protocols import Validator
from referencing import Registry

from .data_operation_json import finite_json_loads

_DIALECTS = {
    "http://json-schema.org/draft-07/schema#": Draft7Validator,
    "https://json-schema.org/draft/2020-12/schema": Draft202012Validator,
}


@lru_cache(maxsize=256)
def prepared_schema_validator(content: bytes) -> Validator:
    """Own checked schema bytes and resolve references only within that captured document."""
    schema = finite_json_loads(content)
    if not isinstance(schema, dict) or schema.get("$schema") not in _DIALECTS:
        raise ValueError("JSON Schema requires an explicit supported dialect")
    validator = _DIALECTS[schema["$schema"]]
    validator.check_schema(schema)
    return validator(schema, registry=Registry())
