"""Capture closed nominal JSON schema graphs without importing candidate Python."""

from __future__ import annotations

from .data_operation_parameters import _draft7
from .data_operation_wire import checked_json_schema, schema_closure


def _tuples(schema):
    """Retain Pydantic fixed-tuple constraints in the selected native Draft7 dialect."""
    if isinstance(schema, list):
        return [_tuples(value) for value in schema]
    if not isinstance(schema, dict):
        return schema
    result = dict(schema)
    for key in ("properties", "patternProperties", "definitions", "$defs"):
        if key in result:
            result[key] = {name: _tuples(value) for name, value in result[key].items()}
    for key in (
        "allOf",
        "anyOf",
        "oneOf",
        "items",
        "prefixItems",
        "additionalItems",
        "additionalProperties",
        "contains",
        "propertyNames",
        "not",
        "if",
        "then",
        "else",
    ):
        if key in result:
            result[key] = _tuples(result[key])
    if "dependencies" in result:
        result["dependencies"] = {
            name: value if isinstance(value, list) else _tuples(value)
            for name, value in result["dependencies"].items()
        }
    if "$defs" in result and "definitions" in result:
        raise ValueError("schema mixes definition dialects")
    if "prefixItems" in result:
        if "additionalItems" in result:
            raise ValueError("schema mixes tuple dialect constraints")
        result["additionalItems"] = result.pop("items", True)
        result["items"] = result.pop("prefixItems")
    if any(
        key in result
        for key in (
            "$dynamicRef",
            "$dynamicAnchor",
            "unevaluatedItems",
            "unevaluatedProperties",
            "dependentSchemas",
            "dependentRequired",
        )
    ):
        raise ValueError("nominal schema contains unsupported non-Draft7 constraints")
    return result


def nominal_schema_kinds(schema, *, namespace, root_name):
    """Project supplied schema bytes into the existing compiler kind vocabulary.

    The trusted producer captures its DTO-generated schema and original source as
    ordinary preparation custody. This helper/compiler executes no DTO or candidate
    code; one source artifact owns the root and all its closed local definitions.
    """
    schema = _draft7(_tuples(schema))
    checked_json_schema(schema)
    definitions = schema.get("definitions", {})
    if not isinstance(root_name, str) or not root_name or root_name in definitions:
        raise ValueError("nominal schema root collides with a local definition")
    records = {
        root_name: schema,
        **{name: schema_closure(value, definitions) for name, value in definitions.items()},
    }
    return tuple(
        {"id": namespace + name, "name": name, "nominal_namespace": namespace, "json_schema": value}
        for name, value in sorted(records.items())
    )


def effective_nominal_kind_declarations(model):
    """Project authenticated compiled shape owners for source correspondence checks.

    These normalized artifacts are derived semantic projections, not the bytes of
    the original authoring documents. The caller supplies its admitted model just
    as it supplies prepared class definitions/vocabularies. Candidate Python never
    imports DTOs or injects an alternative schema during this runtime check.
    """
    import json

    from .data_operation_model import MODEL_VERSION
    from .identity import canonical_bytes
    from .types import SourceArtifact

    owners = {}
    for kind in model.kinds:
        facts = json.loads(kind.facts)
        if facts.get("nominal_namespace") is None:
            continue
        source_owners = {origin.source for origin in kind.origins}
        if len(source_owners) != 1:
            raise ValueError("compiled nominal kind requires one supplied source owner")
        owner = next(iter(source_owners))
        owners.setdefault(owner, []).append(facts)
    return tuple(
        SourceArtifact(
            "effective-nominal-kinds/" + owner,
            canonical_bytes(
                {"version": MODEL_VERSION, "kinds": sorted(records, key=lambda value: value["id"])}
            ),
        )
        for owner, records in sorted(owners.items())
    )
