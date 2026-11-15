"""Captured finite nominal packets retain exact member bodies and explicit project context."""

import json
from decimal import Decimal
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
from corpus_structure.semantic.data_operation_json import DdoJsonValue, json_loads
from corpus_structure.semantic.data_operation_ports import PortRefusal, project_product_members
from corpus_structure.semantic.data_operation_storage import data_operation_definition_projection
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.nominal_schema_kinds import nominal_schema_kinds
from corpus_structure.semantic.types import PreparationError, SourceArtifact
from semantic.data_operation_declaration_support import contract, declarations
from semantic.record_contracts_support import release_inputs


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    member_type: Literal["fact"]
    predicate: str


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    member_type: Literal["finding"]
    reason: str


type Body = Fact | Finding


class Context(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str
    subject_definition: str
    original_source: str | None
    analyzed_scope: DdoJsonValue


class Packet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    member_id: str
    kind_contract: str
    context: Context
    body: Body


class Container(BaseModel):
    model_config = ConfigDict(extra="forbid")
    members: tuple[Packet, ...]


PREFIX = "urn:current-rich:"


def captured_model(change=lambda records: None):
    records = json.loads(canonical_bytes(nominal_schema_kinds(
        Container.model_json_schema(), namespace=PREFIX, root_name="Container"
    )))
    change(records)
    operation = contract(subject="knowledge-universe", subject_definition={
        "id": "knowledge-universe", "identifier_kind": "string", "scope": "project"
    })
    operation["roles"][1]["kind"] = PREFIX + "Container"
    source = SourceArtifact("rich-kinds.json", canonical_bytes({"version": MODEL_VERSION, "kinds": records}))
    return compile_data_operations(declarations=(*declarations(operation), source))


def kind_contract(model, name):
    return next(item.key for item in model.identities if item.domain == "kind" and item.owner == PREFIX + name)


def value(model):
    return {"members": [{
        "member_id": "fact:original", "kind_contract": kind_contract(model, "Fact"),
        "context": {"subject": "project-universe", "subject_definition": "knowledge-universe",
                    "original_source": None, "analyzed_scope": "selected-knowledge"},
        "body": {"member_type": "fact", "predicate": "actual:predicate"},
    }, {
        "member_id": "finding:original", "kind_contract": kind_contract(model, "Finding"),
        "context": {"subject": "project-universe", "subject_definition": "knowledge-universe",
                    "original_source": None, "analyzed_scope": "selected-knowledge"},
        "body": {"member_type": "finding", "reason": "scientific comparison undecided"},
    }]}


def test_closed_nominal_union_projects_each_actual_kind_with_explicit_null_source():
    model = captured_model()
    assert derive_member_kinds(model, PREFIX + "Container") == (PREFIX + "Fact", PREFIX + "Finding")
    projected = tuple(json.loads(item) for item in project_product_members(model, PREFIX + "Container", value(model)))
    assert [item["member_id"] for item in projected] == ["fact:original", "finding:original"]
    assert all("original_source" in item["context"] and item["context"]["original_source"] is None for item in projected)
    assert projected[0]["body"] == ["mapping", [["member_type", ["string", "fact"]], ["predicate", ["string", "actual:predicate"]]]]


@pytest.mark.parametrize("defect", ["different-body", "extra-body-field", "missing-source", "unadmitted-subject"])
def test_closed_nominal_packet_refuses_relabelled_or_unchecked_member_meaning(defect):
    model = captured_model()
    actual = value(model)
    packet = actual["members"][0]
    if defect == "different-body":
        packet["body"] = actual["members"][1]["body"]
    elif defect == "extra-body-field":
        packet["body"]["invented"] = "unchecked"
    elif defect == "missing-source":
        packet["context"].pop("original_source")
    else:
        packet["context"]["subject_definition"] = "not-admitted"
    with pytest.raises(PortRefusal):
        project_product_members(model, PREFIX + "Container", actual)


@pytest.mark.parametrize("defect", ["open", "ambiguous", "generic"])
def test_member_derivation_refuses_open_ambiguous_or_generic_body_authority(defect):
    # All local copies are changed together so the compiler's captured-owner equality
    # remains valid; this tests member semantics rather than a forged archive refusal.
    def change(records):
        def walk(item):
            if isinstance(item, list):
                for child in item:
                    walk(child)
            elif isinstance(item, dict):
                if item.get("title") == "Fact":
                    if defect == "open":
                        item["additionalProperties"] = True
                    elif defect == "ambiguous":
                        item["properties"]["member_type"]["const"] = "finding"
                if defect == "generic" and item.get("title") == "Packet":
                    item["properties"]["body"] = {}
                for child in item.values():
                    walk(child)
        walk(records)
        from corpus_structure.semantic.data_operation_wire import schema_closure
        for record in records:
            schema = record["json_schema"]
            definitions = schema.pop("definitions", {})
            record["json_schema"] = schema_closure(schema, definitions)
    model = captured_model(change)
    with pytest.raises(PreparationError, match="closed nominal|disjoint|required|generic JSON"):
        derive_member_kinds(model, PREFIX + "Container")


def test_native_definition_projection_uses_exact_nominal_member_contracts():
    model = captured_model()
    projection = json.loads(data_operation_definition_projection(release_inputs()[2], model, native_digest="test-native-cut"))
    kinds = {item["kind"]: item for item in projection["kinds"]}
    container = kinds[PREFIX + "Container"]
    assert container["member_contracts"] == [kind_contract(model, "Fact"), kind_contract(model, "Finding")]
    from corpus_structure.semantic.data_operation_wire import validate_wire_schema
    assert validate_wire_schema(container["member_schema"], value(model)["members"][0]["body"])["member_type"] == "fact"
    for name in ("Fact", "Finding"):
        assert kinds[PREFIX + name]["member_contracts"] == []


def test_member_projection_keeps_fractional_context_scope_as_actual_json_numbers():
    model = captured_model()
    actual = value(model)
    scope = {"threshold": Decimal("0.123456789012345678901234567890123456789")}
    actual["members"][0]["context"]["analyzed_scope"] = scope
    projected = project_product_members(model, PREFIX + "Container", actual)
    assert json_loads(projected[0])["context"]["analyzed_scope"] == scope
