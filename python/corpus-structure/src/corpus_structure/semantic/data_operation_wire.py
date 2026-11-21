"""One captured closed Draft7 contract for native, Python and effective wire kinds.

The protocol YAML is authoritative. jsonschema's selected Draft7Validator checks
schemas before use; every reference is local and authenticated before resolution.
See https://python-jsonschema.readthedocs.io/en/stable/validate/ and
https://github.com/supabase/pg_jsonschema for the shared validation realization.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

import yaml
from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError, ValidationError
from pydantic import TypeAdapter
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue
from pydantic_core import core_schema

from .data_operation_json import json_bytes, own_wire_json_value
from .identity import canonical_bytes
from .schema_validation import PreparedSchemaValidator, prepared_schema_validator
from .types import SourceArtifact

DRAFT7 = "http://json-schema.org/draft-07/schema#"
PROTOCOL_SOURCE = "native/data-operation-protocol.yaml"
KIND_PREFIX = "urn:corpus:data-wire:"
type ExactJSONValue = (
    dict[str, ExactJSONValue] | list[ExactJSONValue] | str | bool | int | float | Decimal | None
)
_JSON_VALUE = TypeAdapter(ExactJSONValue)


def _protocol_content(sources: tuple[SourceArtifact, ...] | None) -> bytes:
    if sources is None:
        from .native_protocol_model import ambient_protocol_content

        return ambient_protocol_content()
    return _prepare_protocol_content(sources)


def _prepare_protocol_content(sources: tuple[SourceArtifact, ...] | None) -> bytes:
    if sources is None:
        return _build_protocol_content(None)
    from .data_operation_execution_evidence import SOURCE as EVIDENCE
    from .data_operation_support import ORIGINAL_SUPPORT_REFERENCE_SCHEMA
    from .data_operation_visual_read import SOURCE as VISUAL
    from .pdf_source_search import CONTRACT
    from .record_policy_native import EVENT_FRAME_SCHEMA_SOURCE, GRADE_SCHEMA_SOURCE

    names = {
        PROTOCOL_SOURCE,
        EVIDENCE,
        VISUAL,
        CONTRACT,
        EVENT_FRAME_SCHEMA_SOURCE,
        GRADE_SCHEMA_SOURCE,
        ORIGINAL_SUPPORT_REFERENCE_SCHEMA,
    }
    return _captured_protocol_content(tuple(source for source in sources if source.name in names))


@lru_cache(maxsize=16)
def _captured_protocol_content(sources: tuple[SourceArtifact, ...]) -> bytes:
    return _build_protocol_content(sources)


def _build_protocol_content(sources: tuple[SourceArtifact, ...] | None) -> bytes:
    if sources is None:
        from corpus_structure.model.compiled import model_source

        content = model_source("data-operation-native.yaml")
    else:
        selected = [s.content for s in sources if s.name == PROTOCOL_SOURCE]
        if len(selected) != 1:
            raise ValueError("closed native protocol requires exactly one captured source")
        content = selected[0]
    # This optional companion contract is generated from the actual transport DTO.
    # Captured interpretation must consume its captured schema, never ambient code.
    document = yaml.safe_load(content)
    declared = document.get("definitions") if isinstance(document, dict) else None
    search = (
        declared.get("ensure_pdf_search_projection_request") if isinstance(declared, dict) else None
    )
    if isinstance(search, dict) and search.get("properties", {}).get("configuration") == {
        "x-corpus-source": "pdf-search-configuration"
    }:
        from .pdf_source_search import CONTRACT, search_configuration

        if sources is None:
            from .metadata import get_metadata

            configuration = search_configuration(get_metadata())
        else:
            captured_configuration = [s.content for s in sources if s.name == CONTRACT]
            if len(captured_configuration) != 1:
                raise ValueError("wire PDF search requires its captured configuration")
            configuration = json.loads(captured_configuration[0]).get("configuration")
            if not isinstance(configuration, str) or not configuration:
                raise ValueError("wire PDF search configuration is invalid")
        search["properties"]["configuration"] = {"const": configuration}
        content = canonical_bytes(document)
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
    if "read_selected_visual_evidence_result" in document.get("definitions", {}):
        from .data_operation_visual_read import SOURCE, visual_read_schema

        if sources is None:
            captured = visual_read_schema()
        else:
            values = [source.content for source in sources if source.name == SOURCE]
            if len(values) != 1:
                raise ValueError("visual read requires its captured projection schema")
            captured = values[0]
        extension = checked_json_schema(json.loads(captured))
        definitions = dict(extension.get("definitions", {}))
        definitions["selected_visual_read"] = {
            key: value for key, value in extension.items() if key not in {"definitions", "$schema"}
        }
        if definitions.keys() & document["definitions"].keys():
            raise ValueError("visual read definition collides with protocol")
        document["definitions"].update(definitions)
        content = canonical_bytes(document)
    if "read_selected_feature_fit_frame_result" in document.get("definitions", {}):
        from .record_policy_native import (
            EVENT_FRAME_SCHEMA_SOURCE,
            GRADE_SCHEMA_SOURCE,
            operation_event_frame_schema,
            record_policy_grade_schema,
        )

        for source_name, factory, root in (
            (GRADE_SCHEMA_SOURCE, record_policy_grade_schema, "selected_record_grade"),
            (
                EVENT_FRAME_SCHEMA_SOURCE,
                operation_event_frame_schema,
                "selected_operation_event_frame",
            ),
        ):
            if sources is None:
                captured = factory()
            else:
                values = [source.content for source in sources if source.name == source_name]
                if len(values) != 1:
                    raise ValueError("feature fitting requires its exact captured frame schemas")
                captured = values[0]
            extension = checked_json_schema(json.loads(captured))
            definitions = dict(extension.get("definitions", {}))
            definitions[root] = {
                key: value
                for key, value in extension.items()
                if key not in {"definitions", "$schema"}
            }
            if definitions.keys() & document["definitions"].keys():
                raise ValueError("fit frame definition collides with native protocol")
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


def _lower_set_operations(protocol: dict[str, Any]) -> None:
    """Derive set transports from their single item operation catalogue."""
    operations = {operation["name"]: operation for operation in protocol["operations"]}
    definitions = protocol["definitions"]
    for operation in protocol["operations"]:
        if "item_operation" not in operation:
            continue
        item = operations.get(operation["item_operation"])
        if item is None or item["profile"] != "item":
            raise ValueError("set transport requires a private item operation")
        shared = operation["shared"]
        request = definitions[item["request"]]
        item_request = json.loads(json.dumps(request))
        for name in shared:
            item_request["properties"].pop(name, None)
            if name in item_request["required"]:
                item_request["required"].remove(name)
        item_name = operation["name"] + "_item"
        definitions[item_name] = item_request
        definitions[operation["request"]] = {
            "type": "object",
            "properties": {
                **shared,
                "items": {"type": "array", "items": {"$ref": "#/definitions/" + item_name}},
            },
            "required": [*shared, "items"],
            "additionalProperties": False,
        }
        result = definitions[item["result"]]
        outcomes: list[dict[str, Any]] = []
        for variant in result.get("oneOf", [result]):
            field = variant["properties"][operation["outcome_field"]]
            states = field.get("enum", [field.get("const")])
            for state in states:
                if not isinstance(state, str):
                    raise ValueError("set item result requires finite named outcomes")
                properties = {"state": {"const": state}}
                if set(variant["properties"]) != {operation["outcome_field"]}:
                    result_name = operation["name"] + "_" + state.replace("-", "_") + "_result"
                    result_variant = json.loads(json.dumps(variant))
                    result_variant["properties"][operation["outcome_field"]] = {"const": state}
                    definitions[result_name] = result_variant
                    properties["result"] = {"$ref": "#/definitions/" + result_name}
                outcomes.append(
                    {
                        "type": "object",
                        "properties": properties,
                        "required": list(properties),
                        "additionalProperties": False,
                    }
                )
        outcomes.append(
            {
                "type": "object",
                "properties": {
                    "state": {"const": "refused"},
                    "sqlstate": {
                        "type": "string",
                        "minLength": 5,
                        "maxLength": 5,
                        "pattern": "^[0-9A-Z]{5}$",
                    },
                    "reason": {"type": "string", "minLength": 1},
                },
                "required": ["state", "sqlstate", "reason"],
                "additionalProperties": False,
            }
        )
        definitions[operation["result"]] = {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"oneOf": outcomes}}},
            "required": ["items"],
            "additionalProperties": False,
        }


@lru_cache(maxsize=16)
def _checked_protocol(content: bytes) -> bytes:
    from corpus_structure.schema.integrity import integrity

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
            or set(operation) - {"item_operation", "shared", "outcome_field"}
            != {"name", "profile", "request", "result", "purposes"}
            or operation["profile"] not in {"command", "read", "item"}
        ):
            raise ValueError("invalid native wire operation")
        purposes = operation["purposes"]
        if (
            not isinstance(purposes, list)
            or not purposes
            or any(
                not isinstance(p, str)
                or p not in integrity().purposes
                or integrity().purpose_role(p) is None
                for p in purposes
            )
            or len(purposes) != len(set(purposes))
        ):
            raise ValueError("native wire operation requires unique explicit purpose capabilities")
        if not isinstance(operation["name"], str) or not operation["name"]:
            raise ValueError("native wire operation requires a name")
        set_fields = {"item_operation", "shared", "outcome_field"} & operation.keys()
        if set_fields and (
            set_fields != {"item_operation", "shared", "outcome_field"}
            or operation["profile"] != "command"
            or not isinstance(operation["item_operation"], str)
            or not isinstance(operation["shared"], dict)
            or not isinstance(operation["outcome_field"], str)
        ):
            raise ValueError("invalid native set operation")
        names.append(operation["name"])
    if len(names) != len(set(names)):
        raise ValueError("duplicate native wire operation")
    _lower_set_operations(result)
    for operation in result["operations"]:
        for direction in ("request", "result"):
            if operation[direction] not in result["definitions"]:
                raise ValueError("unresolved native wire operation schema")
    return canonical_bytes(result)


def _protocol(sources: tuple[SourceArtifact, ...] | None) -> dict[str, Any]:
    # The mutable document is a detached compiler/inspection view, never the
    # process's retained preparation or the per-call validation path.
    return json.loads(_protocol_state(sources).checked)


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


def _generated_schema_node(schema):
    """Retain Pydantic fixed-tuple constraints in the selected native Draft7 dialect."""
    if isinstance(schema, list):
        return [_generated_schema_node(value) for value in schema]
    if not isinstance(schema, dict):
        return schema
    result = dict(schema)
    if "format" in result:
        annotation = result.pop("format")
        if "x-ddo-format" in result and result["x-ddo-format"] != annotation:
            raise ValueError("generated schema has conflicting format metadata")
        # pg_jsonschema asserts Draft 7 format by default. This shared profile
        # carries presentation metadata while typed domain owners enforce meaning.
        result["x-ddo-format"] = annotation
    for key in ("properties", "patternProperties", "definitions", "$defs"):
        if key in result:
            result[key] = {
                name: _generated_schema_node(value) for name, value in result[key].items()
            }
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
            result[key] = _generated_schema_node(result[key])
    if "dependencies" in result:
        result["dependencies"] = {
            name: value if isinstance(value, list) else _generated_schema_node(value)
            for name, value in result["dependencies"].items()
        }
    if "$defs" in result and "definitions" in result:
        raise ValueError("schema mixes definition dialects")
    if "$defs" in result:
        result["definitions"] = result.pop("$defs")
    if "$ref" in result:
        reference = result["$ref"]
        if isinstance(reference, str) and reference.startswith("#/$defs/"):
            result["$ref"] = "#/definitions/" + reference.removeprefix("#/$defs/")
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


def generated_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Compile generated local definitions and tuples to the native Draft7 contract.

    Only schema positions are traversed, preserving literal default/const values.
    Caller-authored external contracts continue through checked_json_schema directly.
    """
    normalized = _generated_schema_node(copy.deepcopy(schema))
    if not isinstance(normalized, dict):
        raise ValueError("native wire kind requires an object schema")
    return checked_json_schema({"$schema": DRAFT7, **normalized})


class NativeJsonSchema(GenerateJsonSchema):
    """Project Pydantic-owned constraints into the selected native Draft 7 dialect."""

    def generate(
        self, schema: core_schema.CoreSchema, mode: JsonSchemaMode = "validation"
    ) -> JsonSchemaValue:
        return generated_json_schema(super().generate(schema, mode=mode))


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


@dataclass(frozen=True)
class _PreparedProtocol:
    checked: bytes
    contracts: bytes
    contract_digest: str
    operations: tuple[bytes, ...]
    schemas: Mapping[tuple[str, str], bytes]
    role_kinds: Mapping[tuple[str, str], str]
    validators: Mapping[tuple[str, str], Callable[[Any], Any]]


@lru_cache(maxsize=16)
def _prepared_protocol(content: bytes) -> _PreparedProtocol:
    checked = _checked_protocol(content)
    protocol = json.loads(checked)
    public = [operation for operation in protocol["operations"] if operation["profile"] != "item"]
    contracts = {
        operation["name"]: {
            direction: schema_closure(
                {"$ref": "#/definitions/" + operation[side]}, protocol["definitions"]
            )
            for direction, side in (("input", "request"), ("output", "result"))
        }
        for operation in public
    }
    schemas = {
        (name, direction): canonical_bytes(schema)
        for name, directions in contracts.items()
        for direction, schema in directions.items()
    }
    return _PreparedProtocol(
        checked,
        canonical_bytes(contracts),
        sha256(canonical_bytes(contracts)).hexdigest(),
        tuple(canonical_bytes(operation) for operation in public),
        MappingProxyType(schemas),
        MappingProxyType(
            {
                (operation["name"], direction): KIND_PREFIX + operation[side]
                for operation in public
                for direction, side in (("input", "request"), ("output", "result"))
            }
        ),
        MappingProxyType({key: prepare_wire_schema(schema) for key, schema in schemas.items()}),
    )


def _protocol_state(sources: tuple[SourceArtifact, ...] | None) -> _PreparedProtocol:
    if sources is None:
        from .native_protocol_model import ambient_protocol

        return ambient_protocol()
    return _prepared_protocol(_protocol_content(sources))


def wire_operations(
    sources: tuple[SourceArtifact, ...] | None = None,
) -> tuple[dict[str, Any], ...]:
    """Detached operation facts, including explicit purpose capabilities, from one parser."""
    return tuple(json.loads(operation) for operation in _protocol_state(sources).operations)


def encode_native_wire_request(value: Any) -> str:
    """Retain exact JSON encodability without replaying the SQL request schema."""
    return json_bytes(_JSON_VALUE.validate_python(value, strict=True)).decode()


def wire_contract_digest(sources: tuple[SourceArtifact, ...] | None = None) -> str:
    """Identity of the complete contract installed with the native release."""
    return _protocol_state(sources).contract_digest


def wire_contracts(sources: tuple[SourceArtifact, ...] | None = None) -> dict[str, Any]:
    """Return detached self-contained schemas used verbatim by SQL and Python."""
    return json.loads(_protocol_state(sources).contracts)


@lru_cache(maxsize=256)
def _validator(content: bytes) -> PreparedSchemaValidator:
    schema = checked_json_schema(json.loads(content))
    return prepared_schema_validator(canonical_bytes({"$schema": DRAFT7, **schema}))


def validate_wire_schema(schema: dict[str, Any] | bytes, value: Any) -> Any:
    """Strict JSON-value ingress; return an owned detached snapshot, never coerce."""
    encoded = schema if isinstance(schema, bytes) else canonical_bytes(schema)
    document = json.loads(encoded)
    if "x-corpus-selected-support" in document:
        return prepare_wire_schema(
            encoded,
            contextual_fields=tuple(document["x-corpus-contextual-fields"]),
            frontier_path=(),
        )(value)
    return _validate_wire_value(_validator(encoded), value)


def prepare_wire_schema(
    schema: dict[str, Any] | bytes,
    *,
    contextual_fields: tuple[str, ...] = (),
    frontier_path: tuple[str, ...] | None = None,
) -> Callable[[Any], Any]:
    """Bind schema admission and captured field interpretation to the call's lifetime."""
    encoded = schema if isinstance(schema, bytes) else canonical_bytes(schema)
    return _prepared_wire_schema(encoded, contextual_fields, frontier_path)


@lru_cache(maxsize=256)
def _prepared_wire_schema(encoded, contextual_fields, frontier_path):
    validator = _validator(encoded)
    projector = None
    if contextual_fields:
        from .wire_json_policy import prepare_json_projection

        document = json.loads(encoded)
        declared = prepare_json_projection(document, contextual_fields)
        projector = declared
        if frontier_path is not None:
            from .selected_support_contract import SUPPORT_EXTENSION, SelectedSupportReader

            reader = SelectedSupportReader(document.get(SUPPORT_EXTENSION))

            def project(value):
                projected = declared(value)
                source, target = value, projected
                for key in frontier_path:
                    source, target = source[key], target[key]
                reader.project_page(source, target)
                return projected

            projector = project

    def validate(value: Any) -> Any:
        return _validate_wire_value(validator, value, projector=projector)

    return validate


def _validate_wire_value(validator: PreparedSchemaValidator, value: Any, *, projector=None) -> Any:
    checked = _JSON_VALUE.validate_python(value, strict=True)
    try:
        validator.validate(checked)
    except ValidationError as exc:
        path = "/".join(str(part) for part in exc.absolute_path) or "<root>"
        raise ValueError("native wire violates schema at " + path + ": " + exc.message) from exc
    return (
        own_wire_json_value(checked, preserve_integral_tokens=True)
        if projector is None
        else projector(checked)
    )


def validate_native_wire(
    operation: str,
    direction: Literal["input", "output"],
    value: Any,
    *,
    sources: tuple[SourceArtifact, ...] | None = None,
) -> dict[str, Any]:
    try:
        state = _protocol_state(sources)
        validate = (
            prepare_wire_schema(
                state.schemas[operation, direction],
                contextual_fields=wire_contextual_fields(sources),
                frontier_path=(),
            )
            if operation == "read_demand_result" and isinstance(value, dict)
            else state.validators[operation, direction]
        )
    except KeyError as exc:
        raise ValueError("unknown native wire operation/direction") from exc
    result = validate(value)
    if not isinstance(result, dict):
        raise ValueError("native wire record must be an object")
    return result


def wire_record_schema(name: str, sources=None) -> dict[str, Any]:
    """Return a named closed record from the same captured native schema owner."""
    protocol = _protocol(sources)
    if name not in protocol["definitions"]:
        raise ValueError("unknown native wire record")
    return schema_closure({"$ref": "#/definitions/" + name}, protocol["definitions"])


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
    try:
        return _protocol_state(sources).role_kinds[operation, direction]
    except KeyError as exc:
        raise ValueError("unknown native wire operation/direction") from exc


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


CORRESPONDENCE_SOURCE = "native/data-operation-wire-types.yaml"


def wire_type_name(name: str) -> str:
    return "Wire" + "".join(part[:1].upper() + part[1:] for part in name.split("_"))


def _wire_correspondence_document(sources=None):
    if sources is None:
        content = (
            Path(__file__).resolve().parents[1] / "model/semantic/data-operation-wire-types.yaml"
        ).read_bytes()
    else:
        selected = [s.content for s in sources if s.name == CORRESPONDENCE_SOURCE]
        if len(selected) != 1:
            raise ValueError("wire types require one captured nominal correspondence")
        content = selected[0]
    document = yaml.safe_load(content)
    if (
        not isinstance(document, dict)
        or set(document) != {"version", "fields"}
        or document["version"] != "data-operation-wire-types-v1"
    ):
        raise ValueError("unsupported native wire nominal correspondence")
    return document


def _contextual_fields(document):
    from .wire_json_policy import CONTEXTUAL_JSON_TYPE

    return tuple(
        sorted(
            pointer
            for pointer, nominal in document["fields"].items()
            if nominal == CONTEXTUAL_JSON_TYPE
        )
    )


@lru_cache(maxsize=16)
def _captured_contextual_fields(content: bytes):
    return _contextual_fields(yaml.safe_load(content))


def wire_contextual_fields(sources=None) -> tuple[str, ...]:
    """Acquire D1 roles with their existing current-model or captured-source custody."""
    if sources is None:
        from .native_protocol_model import ambient_contextual_fields

        return ambient_contextual_fields()
    selected = [source.content for source in sources if source.name == CORRESPONDENCE_SOURCE]
    if len(selected) != 1:
        raise ValueError("wire JSON roles require one captured field correspondence")
    return _captured_contextual_fields(selected[0])


def wire_nominal_correspondence(sources=None) -> tuple[tuple[str, str], ...]:
    """Read explicit field identities and JSON roles; never classify by field spelling."""
    from .wire_json_policy import CONTEXTUAL_JSON_TYPE

    document = _wire_correspondence_document(sources)
    protocol = _protocol(sources)
    definitions = protocol["definitions"]
    fields = document["fields"]
    if not isinstance(fields, dict):
        raise ValueError("wire nominal fields must be source pointer bindings")
    fields = dict(fields)
    operations = {operation["name"]: operation for operation in protocol["operations"]}
    for operation in protocol["operations"]:
        if "item_operation" not in operation:
            continue
        item = operations[operation["item_operation"]]
        prefix = "#/definitions/" + item["request"] + "/properties/"
        for pointer, nominal in tuple(fields.items()):
            if not pointer.startswith(prefix):
                continue
            suffix = pointer.removeprefix(prefix)
            target = (
                operation["request"]
                if suffix in operation["shared"]
                else operation["name"] + "_item"
            )
            fields["#/definitions/" + target + "/properties/" + suffix] = nominal
        result = definitions[item["result"]]
        for index, variant in enumerate(result.get("oneOf", [result])):
            field = variant["properties"][operation["outcome_field"]]
            prefix = (
                "#/definitions/"
                + item["result"]
                + ("/oneOf/" + str(index) if "oneOf" in result else "")
                + "/properties/"
            )
            for state in field.get("enum", [field.get("const")]):
                target = operation["name"] + "_" + state.replace("-", "_") + "_result"
                if target not in definitions:
                    continue
                for pointer, nominal in tuple(fields.items()):
                    if pointer.startswith(prefix):
                        fields[
                            "#/definitions/"
                            + target
                            + "/properties/"
                            + pointer.removeprefix(prefix)
                        ] = nominal
    for pointer, nominal in fields.items():
        if not isinstance(nominal, str) or any(
            not part.isidentifier() for part in nominal.split(".")
        ):
            raise ValueError("invalid nominal wire name at " + pointer)
        value = {"definitions": definitions}
        try:
            for part in pointer.removeprefix("#/").split("/"):
                value = value[int(part)] if isinstance(value, list) else value[part]
        except (KeyError, IndexError, ValueError, TypeError) as error:
            raise ValueError("unresolved nominal wire source " + pointer) from error
        if nominal == CONTEXTUAL_JSON_TYPE:
            if not isinstance(value, dict) or value.get("$ref") not in {
                "#/definitions/json_value",
                "#/definitions/DdoJsonValue",
            }:
                raise ValueError(
                    "contextual wire role requires its explicit JSON field: " + pointer
                )
            continue
        while isinstance(value, dict) and "$ref" in value:
            value = definitions[value["$ref"].removeprefix("#/definitions/")]
        alternatives = value.get("anyOf", value.get("oneOf", [value]))
        for alternative in alternatives:
            if "$ref" in alternative:
                alternative = definitions[alternative["$ref"].removeprefix("#/definitions/")]
            if alternative.get("type") not in {"string", "integer", "null"}:
                raise ValueError("nominal wire source is not a scalar identity: " + pointer)
    return tuple(sorted(fields.items()))


def render_wire_types(definitions, nominals=()):
    """Project today's closed structural schema; Draft7 retains all runtime constraints.

    TypedDict keys express omission, unions preserve their individual records and
    arrays remain lists. Exact recursive JSON includes Decimal. No structuring,
    defaults or validation is delegated to these static declarations.
    """
    from keyword import iskeyword

    nominal = dict(nominals)
    classes, aliases, active = {}, {}, set()
    nominal_bases, nominal_imports = {}, {}

    def union(values):
        return " | ".join(dict.fromkeys(values)) or "Never"

    def annotation(value, name, pointer):
        if value is True or value == {}:
            return "WireExactJSONValue"
        if value is False:
            return "Never"
        if not isinstance(value, dict):
            raise ValueError("unsupported structural wire schema at " + pointer)
        if pointer in nominal:
            from .wire_json_policy import CONTEXTUAL_JSON_TYPE

            if nominal[pointer] == CONTEXTUAL_JSON_TYPE:
                module, alias = CONTEXTUAL_JSON_TYPE.rsplit(".", 1)
                nominal_imports[alias] = module
                return alias
            target = value
            while "$ref" in target:
                target = definitions[target["$ref"].removeprefix("#/definitions/")]
            branches = target.get("anyOf", target.get("oneOf", [target]))
            types = []
            for branch in branches:
                while "$ref" in branch:
                    branch = definitions[branch["$ref"].removeprefix("#/definitions/")]
                types.append(branch.get("type"))
            base = "int" if "integer" in types else "str"
            qualified = nominal[pointer]
            alias = qualified.rsplit(".", 1)[-1]
            if "." in qualified:
                module = qualified.rsplit(".", 1)[0]
                if any(not part.isidentifier() or iskeyword(part) for part in qualified.split(".")):
                    raise ValueError("invalid nominal wire owner: " + qualified)
                if alias in nominal_imports and nominal_imports[alias] != module:
                    raise ValueError("inconsistent nominal wire owner: " + alias)
                nominal_imports[alias] = module
            if alias in nominal_bases and nominal_bases[alias] != base:
                raise ValueError("inconsistent nominal wire scalar: " + alias)
            nominal_bases[alias] = base
            return alias + (" | None" if "null" in types else "")
        if "$ref" in value:
            target = value["$ref"].removeprefix("#/definitions/")
            emit(target)
            return wire_type_name(target)
        if "const" in value or "enum" in value:
            literals = value.get("enum", [value.get("const")])
            if any(type(item) not in {str, int, bool, type(None)} for item in literals):
                raise ValueError("unsupported wire literal at " + pointer)
            return "Literal[" + ", ".join(repr(item) for item in literals) + "]"
        typ = value.get("type")
        if typ == "object" or "properties" in value:
            properties = value.get("properties", {})
            additional = value.get("additionalProperties", True)
            if not properties:
                return (
                    "dict[str, "
                    + annotation(additional, name + "Value", pointer + "/additionalProperties")
                    + "]"
                )
            if additional is not False:
                raise ValueError(
                    "mixed open record needs an explicit structural lowering at " + pointer
                )
            fields = []
            for key, child in properties.items():
                if not key.isidentifier() or iskeyword(key):
                    raise ValueError(
                        "unsupported wire record key at " + pointer + "/properties/" + key
                    )
                expression = annotation(
                    child, name + key.title().replace("_", ""), pointer + "/properties/" + key
                )
                presence = "Required" if key in value.get("required", []) else "NotRequired"
                fields.append(f"    {key}: {presence}[{expression}]")
            classes[name] = [f"class {name}(TypedDict):", *fields]
            return name
        for keyword in ("oneOf", "anyOf"):
            if keyword in value:
                return union(
                    annotation(
                        branch,
                        name + "Variant" + str(index + 1),
                        pointer + "/" + keyword + "/" + str(index),
                    )
                    for index, branch in enumerate(value[keyword])
                )
        if "if" in value:
            return union(
                annotation(value[key], name + key.title(), pointer + "/" + key)
                for key in ("then", "else")
                if key in value
            )
        if isinstance(typ, list):
            # The open recursive JSON declaration names its own exact value domain.
            return union(
                annotation({**value, "type": item}, name, pointer + "/type/" + str(index))
                for index, item in enumerate(typ)
            )
        if typ == "array":
            items = value.get("items", True)
            element = (
                union(
                    annotation(
                        child, name + "Item" + str(index + 1), pointer + "/items/" + str(index)
                    )
                    for index, child in enumerate(items)
                )
                if isinstance(items, list)
                else annotation(items, name + "Item", pointer + "/items")
            )
            return "list[" + element + "]"
        primitive = {
            "string": "str",
            "integer": "int",
            "boolean": "bool",
            "number": "int | float | Decimal",
            "null": "None",
        }.get(typ if isinstance(typ, str) else "")
        if primitive:
            return primitive
        raise ValueError("unsupported structural wire schema at " + pointer)

    def emit(key):
        name = wire_type_name(key)
        if name in active or name in aliases or name in classes:
            return
        active.add(name)
        expression = annotation(definitions[key], name, "#/definitions/" + key)
        active.remove(name)
        if expression != name:
            aliases[name] = expression

    for key in sorted(definitions):
        emit(key)
    # A physical fence is the shared source projection of these three protocols,
    # never a second authored DTO or an inferred identity from field spelling.
    fence_sources = (
        "renew_data_request_request",
        "retain_data_completion_intent_request",
        "publish_data_derivation_request",
    )
    fence_fields = ()
    if all(source in definitions for source in fence_sources):
        common = set.intersection(
            *(set(definitions[source]["properties"]) for source in fence_sources)
        )
        source = fence_sources[0]
        fence_fields = tuple(key for key in definitions[source]["properties"] if key in common)
        classes["WireAttemptFence"] = [
            "class WireAttemptFence(TypedDict):",
            *[
                f"    {key}: Required[{annotation(definitions[source]['properties'][key], 'WireAttemptFence' + key.title(), '#/definitions/' + source + '/properties/' + key)}]"
                for key in fence_fields
            ],
        ]
    out = [f"from {module} import {name}" for name, module in sorted(nominal_imports.items())]
    out += [
        "type WireExactJSONValue = dict[str, WireExactJSONValue] | list[WireExactJSONValue] | str | bool | int | float | Decimal | None",
        "",
    ]
    out += [
        f"{name} = NewType({name!r}, {base})"
        for name, base in sorted(nominal_bases.items())
        if name not in nominal_imports
    ]
    for lines in classes.values():
        out += ["", *lines]
    for name, expression in aliases.items():
        out += ["", f"type {name} = {expression}"]
    if fence_fields:
        out += [
            "",
            "def wire_attempt_fence(value: Mapping[str, Any]) -> WireAttemptFence:",
            "    return {",
            *[f"        {key!r}: value[{key!r}]," for key in fence_fields],
            "    }",
        ]
    return "\n".join(out) + "\n"


def generated_wire_source(sources=None):
    """Checkout facade and records use the same structural emitter as archived calls."""
    protocol = _protocol(sources)
    out = [
        '"""Generated closed native wire types and fixed call facade; do not edit."""',
        "from __future__ import annotations",
        "from decimal import Decimal",
        "from collections.abc import Mapping",
        "from typing import Any, Literal, Never, NewType, NotRequired, Required, TypedDict, cast",
        "",
        render_wire_types(protocol["definitions"], wire_nominal_correspondence(sources)),
        "class DataOperationCalls:",
        "    def _invoke(self, name: str, payload: Any) -> Any:",
        "        raise NotImplementedError",
        "",
    ]
    for operation in wire_operations(sources):
        name = operation["name"]
        request, result = (wire_type_name(operation[side]) for side in ("request", "result"))
        out += [
            f"    def {name}(self, payload: {request}) -> {result}:",
            f"        return cast({result}, self._invoke({name!r}, payload))",
            "",
        ]
    return "\n".join(out)


if __name__ == "__main__":
    from corpus_structure.schema.code_generation import _format

    Path(__file__).with_name("_data_operation_wire.py").write_text(
        _format("semantic/_data_operation_wire.py", generated_wire_source())
    )
