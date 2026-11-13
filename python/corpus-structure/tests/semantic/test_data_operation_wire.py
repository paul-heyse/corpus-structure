"""Independent closed-wire types and their effective model correspondence."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema.exceptions import ValidationError

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
from corpus_structure.semantic.data_operation_wire import (
    KIND_PREFIX,
    checked_json_schema,
    validate_native_wire,
    wire_contracts,
    wire_kind_declarations,
    wire_role_kind,
)
from corpus_structure.semantic.identity import canonical_bytes, claim_source_item__data_operation__
from corpus_structure.semantic.types import SourceArtifact


def captured(content: bytes | None = None):
    source = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/data-operation-native.yaml"
    return (SourceArtifact("native/data-operation-protocol.yaml", source.read_bytes() if content is None else content),)


def wire_model(sources=None):
    declaration: dict[str, Any] = copy.deepcopy(claim_source_item__data_operation__)
    declaration["id"] = "data.claim_data_request"
    declaration["roles"][0].update(name="request", parameter="payload", kind=wire_role_kind("claim_data_request", "input", sources))
    declaration["roles"][1].update(name="result", parameter="payload", kind=wire_role_kind("claim_data_request", "output", sources))
    declaration["binding"]["roles"] = ["request"]
    return compile_data_operations(declarations=(SourceArtifact("wire-declarations.json", canonical_bytes({"version": MODEL_VERSION, "operations": [declaration], "kinds": wire_kind_declarations(sources)})),))


@pytest.mark.parametrize("lease", ["3", True, None, 0, 86401])
def test_native_wire_integer_type_and_declared_limits_do_not_coerce(lease):
    with pytest.raises(ValidationError):
        validate_native_wire("claim_data_request", "input", {"request_id": "request:x", "holder": "worker", "lease_seconds": lease})


def test_exact_wire_fields_and_result_variants_are_explicit():
    payload = {"request_id": "request:x", "holder": "worker", "lease_seconds": 3}
    assert validate_native_wire("claim_data_request", "input", payload) == payload
    with pytest.raises(ValidationError):
        validate_native_wire("claim_data_request", "input", {**payload, "extra": 2})
    assert validate_native_wire("claim_data_request", "output", {"state": "no-work"}) == {"state": "no-work"}
    with pytest.raises(ValidationError):
        validate_native_wire("claim_data_request", "output", {"state": "claimed"})
    with pytest.raises(ValidationError):
        validate_native_wire("claim_data_request", "output", {"state": "no-work", "task_id": 4})


def test_shared_wire_contract_is_detached_and_has_only_local_resolved_references():
    contracts = wire_contracts(captured())
    assert len(contracts) == 12
    for directions in contracts.values():
        for schema in directions.values():
            checked_json_schema(schema)
    contracts["claim_data_request"]["input"]["definitions"].clear()
    assert wire_contracts(captured())["claim_data_request"]["input"]["definitions"]
    for schema in ({"$ref": "https://example.invalid/remote"}, {"$ref": "#/definitions/missing"}):
        with pytest.raises(ValueError):
            checked_json_schema(schema)


def test_effective_wire_record_has_the_same_constrained_field_graph():
    model = wire_model(captured())
    owner = KIND_PREFIX + "claim_data_request_request"
    kind = next(k for k in model.kinds if k.semantic_id == owner)
    assert kind.category == "class"
    assert json.loads(kind.facts)["json_schema"]
    lease = next(k for k in model.kinds if k.semantic_id == owner + "/property/lease_seconds")
    facts = json.loads(lease.facts)
    assert facts["range"] == "primitive:integer"
    assert facts["required"] is True
    assert facts["minimum"] == "1"
    assert facts["maximum"] == "86400"
    assert any(e.source == owner and e.target == lease.semantic_id and e.relation == "property" for e in model.edges)
    assert any(e.source == lease.semantic_id and e.target == "primitive:integer" and e.relation == "range" for e in model.edges)
