"""One captured closed Draft7 contract for native, Python and effective wire kinds.

The protocol YAML is authoritative. jsonschema's selected Draft7Validator checks
schemas before use; every reference is local and authenticated before resolution.
See https://python-jsonschema.readthedocs.io/en/stable/validate/ and
https://github.com/supabase/pg_jsonschema for the shared validation realization.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError, ValidationError
from pydantic import JsonValue, TypeAdapter

from .identity import canonical_bytes
from .types import SourceArtifact

DRAFT7 = "http://json-schema.org/draft-07/schema#"
PROTOCOL_SOURCE = "native/data-operation-protocol.yaml"
KIND_PREFIX = "urn:corpus:data-wire:"
_JSON_VALUE = TypeAdapter(JsonValue)


def _protocol_content(sources: tuple[SourceArtifact, ...] | None) -> bytes:
    if sources is None:
        path = Path(__file__).resolve().parents[1] / "model/semantic/data-operation-native.yaml"
        content = path.read_bytes()
    else:
        selected = [s.content for s in sources if s.name == PROTOCOL_SOURCE]
        if len(selected) != 1:
            raise ValueError("closed native protocol requires exactly one captured source")
        content = selected[0]
    # This optional companion contract is generated from the actual transport DTO.
    # Captured interpretation must consume its captured schema, never ambient code.
    document = yaml.safe_load(content)
    declared = document.get("definitions") if isinstance(document, dict) else None
    completion = declared.get("completion") if isinstance(declared, dict) else None
    properties = completion.get("properties") if isinstance(completion, dict) else None
    if isinstance(properties, dict) and "execution_evidence" in properties:
        from .data_operation_execution_evidence import SOURCE, execution_evidence_schema

        if sources is None:
            captured = execution_evidence_schema()
        else:
            values = [source.content for source in sources if source.name == SOURCE]
            if len(values) != 1:
                raise ValueError("native execution evidence requires its captured schema")
            captured = values[0]
        extension = checked_json_schema(json.loads(captured))
        definitions = dict(extension.get("definitions", {}))
        definitions["native_execution_evidence"] = {
            key: value for key, value in extension.items() if key not in {"definitions", "$schema"}
        }
        if definitions.keys() & document["definitions"].keys():
            raise ValueError("native execution evidence definition collides with protocol")
        document["definitions"].update(definitions)
        content = canonical_bytes(document)
    intent_properties = (
        document.get("definitions", {}).get("demand_intent", {}).get("properties", {})
    )
    if "original_sources" in intent_properties:
        from .data_operation_support import (
            ORIGINAL_REFERENCE_SCHEMA,
            original_source_reference_schema,
        )

        if sources is None:
            captured = original_source_reference_schema()
        else:
            values = [
                source.content for source in sources if source.name == ORIGINAL_REFERENCE_SCHEMA
            ]
            if len(values) != 1:
                raise ValueError("original source references require their captured schema")
            captured = values[0]
        extension = checked_json_schema(json.loads(captured))
        definitions = dict(extension.get("definitions", {}))
        definitions["external_source_reference"] = {
            key: value for key, value in extension.items() if key not in {"definitions", "$schema"}
        }
        if definitions.keys() & document["definitions"].keys():
            raise ValueError("original source reference definition collides with protocol")
        document["definitions"].update(definitions)
        content = canonical_bytes(document)
    if "original_document_selection" in document.get("definitions", {}):
        from .data_operation_support import (
            ORIGINAL_SUPPORT_REFERENCE_SCHEMA,
            original_support_reference_schema,
        )

        if sources is None:
            captured = original_support_reference_schema()
        else:
            values = [
                source.content
                for source in sources
                if source.name == ORIGINAL_SUPPORT_REFERENCE_SCHEMA
            ]
            if len(values) != 1:
                raise ValueError("original document references require their captured union schema")
            captured = values[0]
        extension = checked_json_schema(json.loads(captured))
        definitions = dict(extension.get("definitions", {}))
        definitions["original_support_reference"] = {
            key: value for key, value in extension.items() if key not in {"definitions", "$schema"}
        }
        if definitions.keys() & document["definitions"].keys():
            raise ValueError("original support reference definition collides with protocol")
        document["definitions"].update(definitions)
        content = canonical_bytes(document)
    return content


@lru_cache(maxsize=16)
def _checked_protocol(content: bytes) -> bytes:
    result = yaml.safe_load(content)
    if (
        not isinstance(result, dict)
        or set(result) != {"version", "wire_schema_version", "definitions", "operations"}
        or result["version"] != "data-operation-native-v1"
        or result["wire_schema_version"] != "draft7-closed-v1"
    ):
        raise ValueError("unsupported closed native wire protocol")
    if not isinstance(result["definitions"], dict) or not isinstance(result["operations"], list):
        raise ValueError("native wire definitions and operations are required")
    names = []
    for operation in result["operations"]:
        if (
            not isinstance(operation, dict)
            or set(operation) != {"name", "profile", "request", "result", "purposes"}
            or operation["profile"] not in {"command", "read"}
        ):
            raise ValueError("invalid native wire operation")
        purposes = operation["purposes"]
        if (
            not isinstance(purposes, list)
            or not purposes
            or any(
                not isinstance(p, str) or p not in {"read", "write", "evaluate"} for p in purposes
            )
            or len(purposes) != len(set(purposes))
        ):
            raise ValueError("native wire operation requires unique explicit purpose capabilities")
        names.append(operation["name"])
        for direction in ("request", "result"):
            if operation[direction] not in result["definitions"]:
                raise ValueError("unresolved native wire operation schema")
    if len(names) != len(set(names)):
        raise ValueError("duplicate native wire operation")
    return canonical_bytes(result)


def _protocol(sources: tuple[SourceArtifact, ...] | None) -> dict[str, Any]:
    return json.loads(_checked_protocol(_protocol_content(sources)))


def _references(value: Any) -> set[str]:
    """Visit Draft7 schema positions; const/enum payloads are ordinary data."""
    if isinstance(value, bool):
        return set()
    if not isinstance(value, dict):
        raise ValueError("native wire schema position must contain a schema")
    if value.get("$schema", DRAFT7) != DRAFT7:
        raise ValueError("native wire schemas require a single Draft7 dialect")
    if "$id" in value:
        raise ValueError("native wire schemas cannot change the local reference scope")
    result = set()
    if "$ref" in value:
        reference = value["$ref"]
        if (
            not isinstance(reference, str)
            or not reference.startswith("#/definitions/")
            or "/" in reference.removeprefix("#/definitions/")
            or "~" in reference.removeprefix("#/definitions/")
        ):
            raise ValueError("native wire schemas allow only closed local definition references")
        result.add(reference.removeprefix("#/definitions/"))
    for key in ("properties", "patternProperties", "definitions"):
        for child in value.get(key, {}).values():
            result.update(_references(child))
    for key in ("allOf", "anyOf", "oneOf"):
        for child in value.get(key, []):
            result.update(_references(child))
    for key in (
        "additionalItems",
        "additionalProperties",
        "contains",
        "propertyNames",
        "not",
        "if",
        "then",
        "else",
        "items",
    ):
        if key in value:
            children = value[key] if isinstance(value[key], list) else [value[key]]
            for child in children:
                result.update(_references(child))
    for child in value.get("dependencies", {}).values():
        if not isinstance(child, list):
            result.update(_references(child))
    return result


def checked_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Validate the selected dialect and resolve no remote/implicit resource."""
    if not isinstance(schema, dict):
        raise ValueError("native wire kind requires an object schema")
    if schema.get("$schema", DRAFT7) != DRAFT7:
        raise ValueError("native wire schema requires Draft7")
    try:
        Draft7Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError("invalid Draft7 wire schema: " + exc.message) from exc
    definitions = schema.get("definitions", {})
    if not isinstance(definitions, dict) or not _references(schema) <= definitions.keys():
        raise ValueError("unresolved local native wire schema reference")
    return schema


def schema_closure(root: dict[str, Any], definitions: dict[str, Any]) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    pending = list(_references(root))
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        if name not in definitions:
            raise ValueError("unresolved local native wire schema reference: " + name)
        selected[name] = definitions[name]
        pending.extend(_references(definitions[name]) - selected.keys())
    result = {"$schema": DRAFT7, **root}
    if selected:
        result["definitions"] = {name: selected[name] for name in sorted(selected)}
    checked_json_schema(result)
    return result


@lru_cache(maxsize=16)
def _wire_contract_bytes(content: bytes) -> bytes:
    protocol = json.loads(_checked_protocol(content))
    return canonical_bytes(
        {
            operation["name"]: {
                direction: schema_closure(
                    {"$ref": "#/definitions/" + operation[side]}, protocol["definitions"]
                )
                for direction, side in (("input", "request"), ("output", "result"))
            }
            for operation in protocol["operations"]
        }
    )


def wire_operations(
    sources: tuple[SourceArtifact, ...] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Detached operation facts, including explicit purpose capabilities, from one parser."""
    return tuple(_protocol(sources)["operations"])


def wire_contracts(sources: tuple[SourceArtifact, ...] | None = None) -> dict[str, Any]:
    """Return detached self-contained schemas used verbatim by SQL and Python."""
    return json.loads(_wire_contract_bytes(_protocol_content(sources)))


@lru_cache(maxsize=256)
def _validator(content: bytes) -> Draft7Validator:
    schema = checked_json_schema(json.loads(content))
    return Draft7Validator(schema)


def validate_wire_schema(schema: dict[str, Any] | bytes, value: Any) -> Any:
    """Strict JSON-value ingress; return an owned detached snapshot, never coerce."""
    checked = _JSON_VALUE.validate_python(value, strict=True)
    snapshot = canonical_bytes(checked)  # also excludes non-finite JSON numbers
    result = json.loads(snapshot)
    encoded = schema if isinstance(schema, bytes) else canonical_bytes(schema)
    try:
        _validator(encoded).validate(result)
    except ValidationError as exc:
        path = "/".join(str(part) for part in exc.absolute_path) or "<root>"
        raise ValueError("native wire violates schema at " + path + ": " + exc.message) from exc
    return result


@lru_cache(maxsize=256)
def _operation_schema(content: bytes, operation: str, direction: str) -> bytes:
    contracts = json.loads(_wire_contract_bytes(content))
    if direction not in {"input", "output"} or operation not in contracts:
        raise ValueError("unknown native wire operation/direction")
    return canonical_bytes(contracts[operation][direction])


def validate_native_wire(
    operation: str,
    direction: Literal["input", "output"],
    value: Any,
    *,
    sources: tuple[SourceArtifact, ...] | None = None,
) -> dict[str, Any]:
    schema = _operation_schema(_protocol_content(sources), operation, direction)
    result = validate_wire_schema(schema, value)
    if not isinstance(result, dict):
        raise ValueError("native wire record must be an object")
    return result


def wire_kind_declarations(
    sources: tuple[SourceArtifact, ...] | None = None,
) -> tuple[dict[str, Any], ...]:
    protocol = _protocol(sources)
    return tuple(
        {
            "id": KIND_PREFIX + name,
            "name": "wire." + name,
            "scope": "native-wire",
            "json_schema": schema_closure(body, protocol["definitions"]),
            "references": sorted(KIND_PREFIX + target for target in _references(body)),
        }
        for name, body in sorted(protocol["definitions"].items())
    )


def wire_role_kind(operation: str, direction: Literal["input", "output"], sources=None) -> str:
    protocol = _protocol(sources)
    selected = next((item for item in protocol["operations"] if item["name"] == operation), None)
    if selected is None or direction not in {"input", "output"}:
        raise ValueError("unknown native wire operation/direction")
    return KIND_PREFIX + selected["request" if direction == "input" else "result"]


def json_schema_properties(schema: dict[str, Any]) -> tuple[tuple[str, dict[str, Any], bool], ...]:
    """Normalize only actual object fields, preserving every union constraint."""
    checked_json_schema(schema)
    definitions = schema.get("definitions", {})

    def variants(value, active: frozenset[str] = frozenset()):
        if "$ref" in value:
            name = value["$ref"].removeprefix("#/definitions/")
            if name in active:
                return []
            return variants(definitions[name], active | {name})
        if value.get("type") == "object":
            # The base owns common properties; oneOf/anyOf may only constrain
            # their combinations (e.g body_state), not replace that field graph.
            return [value]
        if "oneOf" in value or "anyOf" in value:
            return [
                item
                for branch in value.get("oneOf", value.get("anyOf", []))
                for item in variants(branch, active)
            ]
        return []

    alternatives = variants(schema)
    names = sorted({name for variant in alternatives for name in variant.get("properties", {})})
    result = []
    for name in names:
        choices = []
        for variant in alternatives:
            if name in variant.get("properties", {}):
                field = variant["properties"][name]
                if field not in choices:
                    choices.append(field)
        field = choices[0] if len(choices) == 1 else {"anyOf": choices}
        required = all(name in variant.get("required", []) for variant in alternatives)
        result.append((name, schema_closure(field, definitions), required))
    return tuple(result)


def json_schema_field_type(
    schema: dict[str, Any], *, nominal_namespace: str | None = None
) -> tuple[str, bool]:
    """Project a range without relabelling constrained objects as primitive JSON."""
    root = {key: value for key, value in schema.items() if key not in {"definitions", "$schema"}}
    if "$ref" in root:
        if nominal_namespace is None:
            raise ValueError(
                "unsupported nominal projection for non-wire local JSON Schema references; "
                "use the LinkML or captured Python nominal owner"
            )
        return nominal_namespace + root["$ref"].removeprefix("#/definitions/"), False
    alternatives = root.get("oneOf", root.get("anyOf"))
    if alternatives:
        projected = {
            json_schema_field_type(
                schema_closure(item, schema.get("definitions", {})),
                nominal_namespace=nominal_namespace,
            )
            for item in alternatives
        }
        if len(projected) == 1:
            return projected.pop()
    if root.get("type") == "array" and isinstance(root.get("items"), dict):
        element = schema_closure(root["items"], schema.get("definitions", {}))
        return json_schema_field_type(element, nominal_namespace=nominal_namespace)[0], True
    primitive = root.get("type")
    if primitive is None:
        values = root.get("enum", [root["const"]] if "const" in root else [])
        if values and all(type(value) is str for value in values):
            primitive = "string"
        elif values and all(type(value) is bool for value in values):
            primitive = "boolean"
        elif values and all(type(value) is int for value in values):
            primitive = "integer"
    return "primitive:" + {
        "string": "string",
        "integer": "integer",
        "boolean": "boolean",
        "number": "float",
    }.get(primitive if isinstance(primitive, str) else "", "json"), False


def json_schema_category(schema: dict[str, Any]) -> Literal["class", "type"]:
    """An object record is a class; scalar/collection/heterogeneous values are types."""
    definitions = schema.get("definitions", {})

    def object_record(value, active=frozenset()):
        if "$ref" in value:
            name = value["$ref"].removeprefix("#/definitions/")
            return name not in active and object_record(definitions[name], active | {name})
        alternatives = value.get("oneOf", value.get("anyOf"))
        if alternatives:
            return all(object_record(item, active) for item in alternatives)
        return value.get("type") == "object"

    return "class" if object_record(schema) else "type"
