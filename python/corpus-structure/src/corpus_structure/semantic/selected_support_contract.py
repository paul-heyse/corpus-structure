"""Captured interpretation of the native relation projection and nominal bodies."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, cast

import yaml
from sqlalchemy import Boolean, Integer, Numeric
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from corpus_structure.model.compiled import model_projection, model_source

from .data_operation_json import json_bytes, native_json_loads
from .schema_validation import prepared_schema_validator
from .wire_json_policy import prepare_json_projection

SUPPORT_EXTENSION = "x-corpus-selected-support"


@model_projection
def support_declarations():
    try:
        content = model_source("selected-support.yaml")
    except KeyError as error:
        raise ValueError(
            "captured model has no selected support interpretation; regenerate result"
        ) from error
    document = yaml.safe_load(content)
    if document["version"] != "selected-support-v1":
        raise ValueError("unsupported selected support declaration")
    return document


def omitted_support_fields(relation: str) -> frozenset[str]:
    declarations = support_declarations()
    selected = declarations["relations"].get(relation, {})
    return frozenset((*declarations["omitted"], *selected.get("omitted", ())))


def _column_schema(column) -> dict[str, Any]:
    typ = column.type
    if isinstance(typ, JSONB):
        shape = {}
    elif isinstance(typ, ARRAY):
        from sqlalchemy import Column

        shape = {
            "type": "array",
            "items": _column_schema(Column(type_=typ.item_type, nullable=False)),
        }
    elif isinstance(typ, Boolean):
        shape = {"type": "boolean"}
    elif isinstance(typ, Integer):
        shape = {"type": "integer"}
    elif isinstance(typ, Numeric) or typ.python_type is float:
        shape = {"type": "number"}
    else:
        shape = {"type": "string"}
    if column.nullable and shape:
        return {"anyOf": [shape, {"type": "null"}]}
    return shape


@model_projection
def ambient_support_contract(relation: str) -> bytes:
    from .data_operation_wire import wire_contextual_fields, wire_record_schema
    from .metadata import table

    declaration = support_declarations()["relations"].get(relation, {})
    schema: dict[str, Any]
    if relation == "ops.data_authority_leaf":
        from .authority_leaf import NativeAuthorityLeaf

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            **NativeAuthorityLeaf.model_json_schema(),
        }
    elif relation == "ops.data_execution_evidence_leaf":
        from .execution_evidence_leaf import execution_evidence_leaf_schema

        schema = execution_evidence_leaf_schema()
    elif relation == "ops.data_support_explanation":
        schema = support_declarations()["explanation_schema"]
    else:
        try:
            columns = table(relation).c
        except KeyError as error:
            raise ValueError("unsupported selected support relation: " + relation) from error
        properties = {
            column.name: _column_schema(column)
            for column in columns
            if column.name not in omitted_support_fields(relation)
        }
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }
    contracts = declaration.get("json_contracts", {})
    if contracts:
        schema_properties = cast(dict[str, Any], schema["properties"])
        definitions = schema.setdefault("definitions", {})
        for field, target in contracts.items():
            selected = wire_record_schema(target["record"])
            for name, definition in selected["definitions"].items():
                if name in definitions and definitions[name] != definition:
                    raise ValueError("conflicting captured support schema definition: " + name)
                definitions[name] = definition
            reference = {"$ref": "#/definitions/" + target["record"]}
            schema_properties[field] = (
                {"type": "array", "items": reference} if target["many"] else reference
            )
    schema.setdefault("$schema", "http://json-schema.org/draft-07/schema#")
    contextual = ["#/properties/" + name for name in declaration.get("contextual", ())]
    if "definitions" in schema:
        contextual.extend(wire_contextual_fields())
    return json_bytes(
        {
            "schema": schema,
            "contextual_fields": contextual,
            "kind_body": declaration.get("kind_body"),
        }
    )


@lru_cache(maxsize=128)
def _prepared_support_projection(content: bytes):
    contract = native_json_loads(content)
    schema = contract["schema"]
    # Leaf schemas can be Draft 2020-12. Their ordinary JSON interpretation has
    # no contextual scope; structural admission stays with their owning validator.
    projection = prepare_json_projection(schema, tuple(contract["contextual_fields"]))
    return contract, projection


@lru_cache(maxsize=128)
def _kind_projection(content: bytes):
    return prepare_json_projection(native_json_loads(content), ())


class SelectedSupportReader:
    """Interpret admitted rows using explicitly acquired relation contracts."""

    def __init__(self, contracts: dict[str, Any] | None = None, *, kinds=None, wire_schema=None):
        self.contracts = (
            None
            if contracts is None
            else {name: json_bytes(contract) for name, contract in contracts.items()}
        )
        self.kinds = None if kinds is None else native_json_loads(json_bytes(kinds))
        self.wire_schema = (
            None if wire_schema is None else native_json_loads(json_bytes(wire_schema))
        )

    def contract(self, relation: str) -> bytes:
        if self.contracts is None:
            return ambient_support_contract(relation)
        try:
            return self.contracts[relation]
        except KeyError as error:
            raise ValueError("unsupported captured support relation: " + relation) from error

    def record(self, row, *, validate=True):
        relation = row["relation"]
        contract, project = _prepared_support_projection(self.contract(relation))
        if validate and self.contracts is not None:
            prepared_schema_validator(json_bytes(contract["schema"])).validate(row["record"])
        body = project(row["record"])
        kind_body = contract.get("kind_body")
        if kind_body is not None and self.kinds is not None:
            kind_id = body["kind_contract"]
            if kind_id not in self.kinds:
                raise ValueError("unsupported captured support kind: " + kind_id)
            kind = self.kinds[kind_id]
            # Structural and semantic admission remain with the native/captured
            # closure validator. The same captured kind selects interpretation.
            body[kind_body] = _kind_projection(json_bytes(kind["meaning_schema"]))(
                row["record"][kind_body]
            )
        return {"key": row["key"], "relation": relation, "record": body}

    def loads(self, content: bytes | str, *, validate=True):
        return self.record(native_json_loads(content), validate=validate)

    def frontier(self, kind, value):
        from .data_operation_wire import wire_contextual_fields, wire_record_schema

        name = {
            "obligations": "result_obligation",
            "uses": "result_use",
            "original_source_admissions": "original_source_admission_result",
        }[kind]
        schema = (
            wire_record_schema(name)
            if self.wire_schema is None
            else {"$ref": "#/definitions/" + name, "definitions": self.wire_schema["definitions"]}
        )
        roles = (
            wire_contextual_fields()
            if self.wire_schema is None
            else tuple(self.wire_schema["x-corpus-contextual-fields"])
        )
        return prepare_json_projection(schema, roles)(value)

    def capture(self, relations):
        return {
            relation: native_json_loads(self.contract(relation)) for relation in sorted(relations)
        }

    def project_page(self, source, projected):
        support = source.get("support_page")
        if support is None:
            return
        if source.get("view", "frontier") == "frontier":
            raise ValueError("frontier JSON interpretation requires an absent support page")
        projected["support_page"]["records"] = [self.record(row) for row in support["records"]]


def prepare_demand_interpretation(schema, contextual_fields):
    """Prepare field roles separately from native or captured structural admission."""
    declared = prepare_json_projection(schema, tuple(contextual_fields))
    reader = SelectedSupportReader(schema.get(SUPPORT_EXTENSION))

    def interpret(value):
        try:
            projected = declared(value)
        except (TypeError, AttributeError, KeyError) as error:
            raise ValueError("native demand fields differ from their declared structure") from error
        reader.project_page(value, projected)
        return projected

    return interpret
