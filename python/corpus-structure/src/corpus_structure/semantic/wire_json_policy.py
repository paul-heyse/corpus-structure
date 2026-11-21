"""Prepare native JSON interpretation from captured schema field correspondences."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from jsonschema.exceptions import ValidationError

from .data_operation_json import json_bytes, own_native_json_value
from .schema_validation import prepared_schema_validator

CONTEXTUAL_JSON_TYPE = "corpus_structure.semantic.data_operation_json.ContextualJsonValue"
_ORDINARY_JSON = {"#/definitions/json_value", "#/definitions/DdoJsonValue"}


def prepare_json_projection(schema: dict[str, Any], contextual_fields: tuple[str, ...]):
    """Compile only distinguishing field roles and typed integer coordinates.

    The native schema admits exact number tokens first. Its ordinary JSON aliases
    are opaque data, and equally projected union branches share one converter.
    """
    definitions = schema.get("definitions", {})
    contextual = frozenset(contextual_fields)
    compiled = {}

    def ordinary(value):
        return own_native_json_value(value)

    def resolve(node):
        while isinstance(node, dict) and "$ref" in node:
            node = definitions[node["$ref"].removeprefix("#/definitions/")]
        return node

    def needed(node, pointer, active=frozenset()):
        if pointer in contextual:
            return True
        if not isinstance(node, dict) or not node:
            return False
        if "$ref" in node:
            reference = node["$ref"]
            return reference not in _ORDINARY_JSON and reference not in active and needed(
                resolve(node), reference, active | {reference}
            )
        if node.get("type") == "integer":
            return True
        for key in ("properties", "patternProperties"):
            if any(needed(child, pointer + "/" + key + "/" + name, active) for name, child in node.get(key, {}).items()):
                return True
        for key in ("items", "additionalProperties", "additionalItems", "then", "else"):
            child = node.get(key, {})
            if isinstance(child, list):
                if any(needed(item, pointer + "/" + key + "/" + str(index), active) for index, item in enumerate(child)):
                    return True
            elif needed(child, pointer + "/" + key, active):
                return True
        return any(needed(child, pointer + "/" + key + "/" + str(index), active) for key in ("anyOf", "oneOf", "allOf") for index, child in enumerate(node.get(key, [])))

    def predicate(node, *, disjoint_types=False):
        selected = resolve(node)
        # Native-admitted tagged records and disjoint JSON types need no schema replay.
        if isinstance(selected, dict):
            constants = {key: child["const"] for key, child in selected.get("properties", {}).items() if isinstance(child, dict) and "const" in child and key in selected.get("required", ())}
            if constants:
                return lambda value: isinstance(value, dict) and all(value.get(key) == expected for key, expected in constants.items())
            typ = selected.get("type")
            classes = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}
            if disjoint_types and isinstance(typ, str) and typ in classes:
                return lambda value: type(value) is classes[typ]
        # Only an actually differing, non-disjoint branch reaches a schema predicate.
        validator = prepared_schema_validator(json_bytes({"$schema": "http://json-schema.org/draft-07/schema#", "definitions": definitions, **node}))

        def valid(value):
            try:
                validator.validate(value)
            except ValidationError:
                return False
            return True

        return valid

    def compile_node(node, pointer):
        if pointer in compiled:
            return compiled[pointer]
        if not needed(node, pointer):
            return ordinary, None
        target = ordinary

        def project(value):
            return target(value)

        compiled[pointer] = (project, ("recursive", pointer))
        if pointer in contextual:
            def contextual_value(value):
                return own_native_json_value(value, contextual=True)

            target = contextual_value
            shape = ("contextual",)
        elif "$ref" in node:
            reference = node["$ref"]
            target, shape = compile_node(resolve(node), reference)
        elif "oneOf" in node or "anyOf" in node:
            keyword = "oneOf" if "oneOf" in node else "anyOf"
            branches = tuple(compile_node(branch, pointer + "/" + keyword + "/" + str(index)) for index, branch in enumerate(node[keyword]))
            shapes = tuple(shape for _, shape in branches)
            if all(shape == shapes[0] for shape in shapes):
                target, shape = branches[0]
            else:
                types = [resolve(branch).get("type") for branch in node[keyword]]
                disjoint_types = all(isinstance(typ, str) and typ in {"object", "array", "string", "boolean", "null"} for typ in types) and len(set(types)) == len(types)
                alternatives = tuple((predicate(branch, disjoint_types=disjoint_types), convert) for branch, (convert, _) in zip(node[keyword], branches, strict=True))

                def alternative(value):
                    for valid, convert in alternatives:
                        if valid(value):
                            return convert(value)
                    raise ValueError("admitted native JSON has no applicable schema branch")

                target, shape = alternative, ("union", shapes)
        elif node.get("type") == "integer":
            def integer_value(value):
                return int(value) if type(value) is Decimal else ordinary(value)

            target = integer_value
            shape = ("integer",)
        elif node.get("type") == "object" or "properties" in node:
            properties = {key: compile_node(child, pointer + "/properties/" + key) for key, child in node.get("properties", {}).items()}
            properties = {key: value for key, value in properties.items() if value[1] is not None}
            additional, additional_shape = compile_node(node.get("additionalProperties", {}), pointer + "/additionalProperties")
            def object_value(value):
                return {key: properties[key][0](item) if key in properties else additional(item) for key, item in value.items()}

            target = object_value
            shape = ("object", tuple(sorted((key, value[1]) for key, value in properties.items())), additional_shape)
        elif node.get("type") == "array":
            items = node.get("items", {})
            if isinstance(items, list):
                elements = tuple(compile_node(child, pointer + "/items/" + str(index)) for index, child in enumerate(items))
                extra, extra_shape = compile_node(node.get("additionalItems", {}), pointer + "/additionalItems")
                def tuple_values(value):
                    return [(elements[index][0] if index < len(elements) else extra)(item) for index, item in enumerate(value)]

                target = tuple_values
                shape = ("tuple", tuple(item[1] for item in elements), extra_shape)
            else:
                element, element_shape = compile_node(items, pointer + "/items")
                def array_values(value):
                    return [element(item) for item in value]

                target = array_values
                shape = ("array", element_shape)
        else:
            # No selected field uses a conditional or intersection to change its
            # numeric role. Refuse a future declaration instead of erasing it.
            raise ValueError("native JSON field role needs an explicit structural projection: " + pointer)
        compiled[pointer] = (project, shape)
        return project, shape

    return compile_node(schema, "#")[0]
