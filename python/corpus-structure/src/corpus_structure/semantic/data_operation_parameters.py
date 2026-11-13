"""Nominal operation parameters derived from the same captured boundary authority."""

from __future__ import annotations

import copy
import json
from typing import Any

from .data_operation_identity import semantic_value
from .data_operation_wire import checked_json_schema, validate_wire_schema


def _draft7(schema: Any) -> Any:
    """Normalize Pydantic's local definition spelling without changing constraints."""
    if isinstance(schema, list):
        return [_draft7(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    result = copy.deepcopy(schema)
    for key, value in schema.items():
        if key == "$ref":
            result[key] = value.replace("#/$defs/", "#/definitions/")
        elif key in {"properties", "patternProperties", "definitions", "$defs"}:
            result.pop(key, None)
            result["definitions" if key == "$defs" else key] = {
                name: _draft7(child) for name, child in value.items()
            }
        elif key in {
            "allOf",
            "anyOf",
            "oneOf",
            "items",
            "additionalItems",
            "additionalProperties",
            "contains",
            "not",
            "if",
            "then",
            "else",
            "propertyNames",
        }:
            result[key] = _draft7(value)
    return result


def compile_nominal_parameters(parameters, *, schema, definitions, vocabularies, kinds):
    """Compile authored nominal names; generated schemas are never caller-authored."""
    result = copy.deepcopy(parameters)
    nominal = {
        name: definition
        for name, definition in result.items()
        if isinstance(definition, dict) and "kind" in definition
    }
    if not nominal:
        return result
    if schema is None or definitions is None:
        raise ValueError("nominal parameters require captured semantic schema/definitions")
    from .boundary import build_boundary_adapters
    from .data_operation_storage import kind_meaning_schema
    from .prepare import _primitive, _view
    from .types import ClassDefinition, PropertyDefinition

    view = _view(schema)
    class_names = {definition.name for definition in definitions}
    enum_names = {vocabulary.enum for vocabulary in vocabularies}
    primitives = {
        prop.range: _primitive(view, prop.range)
        for definition in definitions
        for prop in definition.properties
        if prop.range not in class_names | enum_names
    }
    aliases = {
        (definition.name, prop.name): view.induced_slot(prop.name, definition.name).alias
        or prop.name
        for definition in definitions
        for prop in definition.properties
    }
    fragments = {
        kind.name: json.loads(kind.facts)["conditional_rules"]
        for kind in kinds.values()
        if "conditional_rules" in json.loads(kind.facts)
    }
    by_name = {kind.name: kind for kind in kinds.values()}
    selected = []
    wrappers = {}
    adapter_definitions = list(definitions)
    for name, definition in nominal.items():
        if set(definition) - {"kind", "collection", "required", "nullable", "default"}:
            raise ValueError("unknown authored nominal parameter field: " + name)
        kind = kinds.get(definition["kind"], by_name.get(definition["kind"]))
        if kind is None or kind.category != "class" or not kind.complete:
            raise ValueError("nominal parameter requires one complete owned class: " + name)
        if definition.get("collection", "scalar") not in {"scalar", "sequence"} or any(
            type(definition[key]) is not bool
            for key in ("required", "nullable")
            if key in definition
        ):
            raise ValueError("invalid nominal parameter collection/presence: " + name)
        definition["kind"] = kind.semantic_id
        definition["collection"] = definition.get("collection", "scalar")
        definition["required"] = definition.get("required", True)
        definition["nullable"] = definition.get("nullable", False)
        wrapper = "DdoParameterBoundary_" + name
        if wrapper in class_names:
            raise ValueError("nominal parameter boundary name collides with an owned class")
        wrappers[name] = wrapper
        adapter_definitions.append(
            ClassDefinition(
                wrapper,
                "urn:corpus:compiler:parameter:" + name,
                (),
                (
                    PropertyDefinition(
                        "value",
                        "urn:corpus:compiler:parameter-value",
                        kind.name,
                        True,
                        False,
                        None,
                        None,
                        None,
                        None,
                        None,
                        True,
                    ),
                ),
                (),
            )
        )
        selected.append(wrapper)
    adapters = dict(
        build_boundary_adapters(
            tuple(adapter_definitions),
            vocabularies,
            primitive_types=primitives,
            aliases=aliases,
            conditional_fragments=fragments,
            class_names=tuple(set(selected)),
        )
    )
    classes = {definition.name: definition for definition in definitions}
    enums = {
        vocabulary.enum: {member.value for member in vocabulary.members}
        for vocabulary in vocabularies
    }
    for name, definition in nominal.items():
        kind = kinds[definition["kind"]]
        wrapper = _draft7(adapters[wrappers[name]].json_schema())
        body = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            **({"definitions": wrapper["definitions"]} if "definitions" in wrapper else {}),
            **wrapper["properties"]["value"],
        }
        meaning = kind_meaning_schema(
            kind, tuple(kinds.values()), classes, lambda name: enums[name]
        )
        for key, value in (("body_schema", body), ("meaning_schema", meaning)):
            definitions_part = {
                field: value[field] for field in ("$schema", "definitions") if field in value
            }
            inner = {field: item for field, item in value.items() if field not in definitions_part}
            if definition["collection"] == "sequence":
                inner = (
                    {"type": "array", "items": inner}
                    if key == "body_schema"
                    else {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": [{"const": "sequence"}, {"type": "array", "items": inner}],
                        "additionalItems": False,
                    }
                )
            if definition["nullable"]:
                null = {"type": "null"} if key == "body_schema" else {"const": ["null"]}
                inner = {"anyOf": [null, inner]}
            definition[key] = checked_json_schema({**definitions_part, **inner})
        if "default" in definition:
            validate_nominal_parameter(definition, definition["default"])
    return result


def validate_nominal_parameter(definition, value):
    """Preserve exact nested primitive tags; JSON display alone cannot type an integer."""
    meaning = semantic_value(value)
    validate_wire_schema(definition["meaning_schema"], meaning)
    from .data_operation_identity import decode_semantic_value

    # The owning semantic codec provides the lossless input; the body schema
    # independently enforces the generated nominal shape and scalar constraints.
    decoded = decode_semantic_value(meaning)
    from typing import Any

    from pydantic import TypeAdapter

    display = TypeAdapter(Any).dump_python(decoded, mode="json")
    validate_wire_schema(definition["body_schema"], display)
    return value
