"""Nested nominal parameters share captured Python/native contracts and exact tags."""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_bindings import effective_binding_parameters
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_storage import data_operation_definition_projection
from corpus_structure.semantic.identity import canonical_bytes
from semantic.data_operation_binding_support import (
    binding_native_connection as binding_native_connection,
)
from semantic.data_operation_declaration_support import PARAMETER
from semantic.data_operation_declaration_support import declaration as build_declaration


@pytest.fixture(scope="module")
def parameter_model():
    schema = SourceBundle(
        "test",
        (
            SourceArtifact(
                "test",
                b"""
id: urn:parameter-test
name: parameter_test
prefixes: {p: 'urn:parameter-test:'}
default_prefix: p
default_range: string
types:
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
  integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
classes:
  Span:
    attributes:
      first: {range: integer, required: true, minimum_value: 0}
      last: {range: integer, required: true, minimum_value: 0}
  Slot:
    abstract: true
    attributes: {kind: {required: true}}
  Count:
    is_a: Slot
    attributes:
      kind: {required: true, equals_string: count}
      value: {range: integer, required: true}
  Label:
    is_a: Slot
    attributes:
      kind: {required: true, equals_string: label}
      value: {required: true}
  Envelope:
    attributes:
      selected: {range: Slot, inlined: true, required: true}
""",
            ),
        ),
    )
    prepared = prepare_release(schema)
    operation = build_declaration(
        "urn:parameter-test:operation",
        vocabulary=PARAMETER,
        roles=[
            dict(
                name="result",
                kind="integer",
                direction="output",
                minimum=1,
                maximum=1,
                collection="scalar",
                presence="required",
            )
        ],
        behavior="parameter-control",
        parameters=dict(
            spans=dict(kind="Span", collection="sequence", default=[]),
            slot=dict(kind="Envelope", required=False, nullable=True),
            direct=dict(kind="Slot", required=False),
        ),
        binding=dict(operator="all", children=[]),
    )
    from corpus_structure.semantic.data_operation_model import MODEL_VERSION

    declaration = SourceArtifact(
        "operations", canonical_bytes(dict(version=MODEL_VERSION, operations=[operation]))
    )
    model = compile_data_operations(
        schema=schema,
        declarations=(declaration,),
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    return prepared, model


def test_nominal_parameter_defaults_missing_null_and_nested_tags(parameter_model):
    _, model = parameter_model
    operation = model.operation("urn:parameter-test:operation")
    assert effective_binding_parameters(operation) == {"spans": []}
    assert effective_binding_parameters(operation, {"slot": None}) == {"spans": [], "slot": None}
    valid = {
        "spans": [{"first": 0, "last": 3}],
        "slot": {"selected": {"kind": "count", "value": 2}},
    }
    assert effective_binding_parameters(operation, valid) == valid
    labels = {"slot": {"selected": {"kind": "label", "value": "actual"}}}
    assert effective_binding_parameters(operation, labels)["slot"] == labels["slot"]
    assert effective_binding_parameters(operation, {"direct": {"kind": "count", "value": 2}})[
        "direct"
    ] == {"kind": "count", "value": 2}
    for invalid in (
        {"spans": None},
        {"spans": [{"first": True, "last": 3}]},
        {"spans": [{"first": 1.0, "last": 3}]},
        {"spans": [{"first": -1, "last": 3}]},
        {"spans": [{"first": 0, "last": 3, "extra": 1}]},
        {"slot": {"selected": {"kind": "count", "value": "2"}}},
        {"slot": {"selected": {"kind": "unknown", "value": 2}}},
        {"undeclared": []},
    ):
        with pytest.raises(ValueError):
            effective_binding_parameters(operation, invalid)
    projected = json.loads(
        data_operation_definition_projection(
            parameter_model[0], model, native_digest="native:control"
        )
    )
    assert {"urn:parameter-test:Span", "urn:parameter-test:Envelope"} <= {
        kind["kind"] for kind in projected["kinds"]
    }


@pytest.mark.parametrize("valid", [True, False])
def test_native_nominal_parameters_enforce_the_same_captured_nested_shape(
    parameter_model, binding_native_connection, valid
):
    _, model = parameter_model
    operation = next(
        item
        for item in json.loads(model.content)["operations"]
        if item["semantic_id"] == "urn:parameter-test:operation"
    )
    params = {
        "spans": [{"first": 0, "last": 3}],
        "slot": {"selected": {"kind": "count", "value": 2 if valid else "2"}},
    }
    selected = dict(parameters=params, parameter_meaning=semantic_value(params))
    query = text(
        "SELECT ops.ddo_validate_parameters("
        "CAST(:operation AS jsonb),CAST(:selection AS jsonb),CAST(:model AS jsonb))"
    )
    values = dict(
        operation=json.dumps(operation),
        selection=json.dumps(selected),
        model=model.content.decode(),
    )
    if valid:
        binding_native_connection.execute(query, values)
    else:
        with (
            pytest.raises(DBAPIError, match="captured schema"),
            binding_native_connection.begin_nested(),
        ):
            binding_native_connection.execute(query, values)
