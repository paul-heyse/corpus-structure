"""Prepared validators for explicitly declared, locally resolved JSON Schema contracts."""

from functools import lru_cache

from jsonschema import Draft7Validator, Draft202012Validator
from jsonschema.protocols import Validator
from referencing import Registry, Resource

from .data_operation_json import finite_json_loads

_DIALECTS = {
    "http://json-schema.org/draft-07/schema#": Draft7Validator,
    "https://json-schema.org/draft/2020-12/schema": Draft202012Validator,
}


@lru_cache(maxsize=256)
def prepared_schema_validator(
    content: bytes, resources: tuple[tuple[str, bytes], ...] = ()
) -> Validator:
    """Prepare an explicit dialect and closed captured reference context.

    Both root and resource bytes participate in the preparation cache key. The empty
    registry's retrieval policy refuses remote references rather than reading a URL.
    """
    schema = finite_json_loads(content)
    if not isinstance(schema, dict) or schema.get("$schema") not in _DIALECTS:
        raise ValueError("JSON Schema requires an explicit supported dialect")
    validator = _DIALECTS[schema["$schema"]]
    validator.check_schema(schema)
    captured = {}
    for uri, resource_content in resources:
        if uri in captured:
            raise ValueError("duplicate captured JSON Schema resource: " + uri)
        value = finite_json_loads(resource_content)
        if not isinstance(value, dict) or value.get("$schema") not in _DIALECTS:
            raise ValueError("captured JSON Schema requires an explicit supported dialect")
        _DIALECTS[value["$schema"]].check_schema(value)
        captured[uri] = Resource.from_contents(value)
    return validator(schema, registry=Registry().with_resources(captured.items()))
