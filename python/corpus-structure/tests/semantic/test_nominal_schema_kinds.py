"""Closed DTO schema owners retain actual nominal edges and native shape constraints."""

import json

import pytest
from jsonschema import Draft7Validator
from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.nominal_schema_kinds import nominal_schema_kinds
from corpus_structure.semantic.types import PreparationError, SourceArtifact
from semantic.data_operation_declaration_support import contract, declarations


class Location(BaseModel):
    model_config = ConfigDict(extra="forbid")
    address: str
    span: tuple[int, int]


class Report(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: Location
    labels: tuple[str, ...]


def kind_source(name="dto-kinds.json", *, records=None):
    return SourceArtifact(
        name,
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "kinds": records
                if records is not None
                else nominal_schema_kinds(
                    Report.model_json_schema(), namespace="urn:declared:report:", root_name="Report"
                ),
            }
        ),
    )


def test_dto_kind_only_source_materializes_local_nominal_graph_and_fixed_tuple():
    value = contract()
    value["roles"][0]["kind"] = "urn:declared:report:Report"
    model = compile_data_operations(declarations=(*declarations(value), kind_source()))
    facts = {item.semantic_id: json.loads(item.facts) for item in model.kinds}
    assert (
        facts["urn:declared:report:Report/property/location"]["range"]
        == "urn:declared:report:Location"
    )
    assert facts["urn:declared:report:Location/property/address"]["range"] == "primitive:string"
    schema = facts["urn:declared:report:Report"]["json_schema"]
    validator = Draft7Validator(schema)
    assert validator.is_valid({"location": {"address": "actual", "span": [2, 7]}, "labels": []})
    assert not validator.is_valid(
        {"location": {"address": "actual", "span": [2, "7"]}, "labels": []}
    )
    assert not validator.is_valid(
        {"location": {"address": "actual", "span": [2, 7, 9]}, "labels": []}
    )
    assert {item.owner for item in model.identities} >= {
        "urn:declared:report:Report",
        "urn:declared:report:Location",
    }


def test_nominal_namespace_refuses_external_unresolved_and_colliding_owners():
    for reference in ("https://example.test/Elsewhere", "#/$defs/Missing"):
        with pytest.raises(ValueError, match=r"closed local|unresolved"):
            nominal_schema_kinds(
                {"type": "object", "properties": {"item": {"$ref": reference}}},
                namespace="urn:closed:",
                root_name="Root",
            )
    records = nominal_schema_kinds(
        Report.model_json_schema(), namespace="urn:declared:report:", root_name="Report"
    )
    with pytest.raises(PreparationError, match="conflicting source owners"):
        compile_data_operations(
            declarations=(kind_source(), kind_source("other-owner.json", records=records))
        )
    forged = json.loads(canonical_bytes(records))
    for record in forged:
        if record["name"] == "Location":
            record["json_schema"]["properties"]["address"]["type"] = "integer"
    with pytest.raises(PreparationError, match="differs from its declared wire owner"):
        compile_data_operations(declarations=(kind_source(records=forged),))


def test_schema_normalization_preserves_const_payloads_and_refuses_dialect_mixing():
    schema = {
        "type": "object",
        "properties": {"value": {"const": {"prefixItems": [1], "items": False}}},
    }
    records = nominal_schema_kinds(schema, namespace="urn:literal:", root_name="Literal")
    assert (
        records[0]["json_schema"]["properties"]["value"]["const"]
        == schema["properties"]["value"]["const"]
    )
    with pytest.raises(ValueError, match="mixes definition dialects"):
        nominal_schema_kinds(
            {"$defs": {}, "definitions": {}}, namespace="urn:mixed:", root_name="Root"
        )
    with pytest.raises(ValueError, match="unsupported non-Draft7"):
        nominal_schema_kinds(
            {"type": "object", "unevaluatedProperties": False},
            namespace="urn:mixed:",
            root_name="Root",
        )


def test_runtime_source_correspondence_reuses_compiled_nominal_owner_and_recomputes_body():
    from dataclasses import replace

    from corpus_structure.semantic.data_operation_ports import PortRefusal, python_port_identity
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    value = contract()
    value["roles"][0].update(kind="urn:declared:report:Report", parameter="value")
    value["roles"][1]["kind"] = "urn:declared:report:Report"
    code = (
        "def derive(value: dict) -> dict:\n    return value\n"
        + f"derive__data_operation__ = {value!r}\n"
    )
    sources = PythonSourceCollection(
        (PythonSource("nominal_runtime", code.encode(), "nominal_runtime.py"),)
    )
    model = compile_data_operations(declarations=(kind_source(),), python_sources=sources)
    identity = python_port_identity(model, sources, value["id"])
    assert identity.recipe == next(
        item.key
        for item in model.identities
        if item.owner == value["id"] and item.domain == "recipe"
    )
    changed = replace(
        sources,
        sources=(
            replace(sources.sources[0], content=code.replace("return value", "return {}").encode()),
        ),
    )
    with pytest.raises(PortRefusal, match="correspondence is unavailable or differs"):
        python_port_identity(model, changed, value["id"])
