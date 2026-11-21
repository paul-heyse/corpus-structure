"""Exact scope JSON; independent literals retain fractional context meaning."""

from decimal import Decimal

import pytest
from sqlalchemy import bindparam, cast, select, text

from corpus_structure.semantic.data_operation_identity import SemanticRequestKey
from corpus_structure.semantic.data_operation_json import (
    JsonBoundaryError,
    finite_json_bytes,
    finite_json_loads,
    json_bytes,
    json_loads,
    native_json_loads,
    wire_json_loads,
)
from corpus_structure.semantic.data_operation_jsonb import ContextJSONB
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_operation_wire import validate_native_wire

PRECISE = b'{"coordinate":0.12345678901234567890123456789,"page":1}'


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("1", True),
        ("1.0", True),
        ("1e0", True),
        ("-0.0", True),
        ("true", False),
        ("1.25", False),
        ("1.00000000000000000000001", False),
        ("9007199254740993.1", False),
        ("1e-999", False),
        ("9223372036854775807", True),
        ("9223372036854775808", False),
    ],
)
def test_typed_integer_tokens_match_native_before_float_projection(
    native_rollback, token, expected
):
    from jsonschema import ValidationError
    from sqlalchemy import JSON, func

    from corpus_structure.semantic.schema_validation import prepared_schema_validator

    schema = b'{"$schema":"http://json-schema.org/draft-07/schema#","type":"integer","minimum":-9223372036854775808,"maximum":9223372036854775807}'
    validator = prepared_schema_validator(schema)
    if expected:
        validator.validate(native_json_loads(token))
    else:
        with pytest.raises(ValidationError):
            validator.validate(native_json_loads(token))
    actual = native_rollback.connection.scalar(
        select(
            func.public.json_matches_schema(
                cast(bindparam("schema"), JSON), cast(bindparam("value"), JSON)
            )
        ),
        {"schema": schema.decode(), "value": token},
    )
    assert actual is expected


def test_integer_wire_boundary_rejects_fraction_before_approximate_projection():
    from corpus_structure.semantic.data_operation_wire import prepare_wire_schema

    validate = prepare_wire_schema(
        {"type": "object", "properties": {"count": {"type": "integer"}}, "required": ["count"]}
    )
    with pytest.raises(ValueError, match="schema"):
        validate(native_json_loads('{"count":1.00000000000000000000001}'))
    whole = validate(native_json_loads('{"count":1.0}'))["count"]
    assert type(whole) is int and whole == 1
    large = validate(native_json_loads('{"count":9007199254740993.0}'))["count"]
    assert type(large) is int and large == 9007199254740993


@pytest.mark.parametrize(
    "content",
    [
        b'{"key":1,"key":2}',
        b'{"nested":{"key":1,"key":2}}',
        b"NaN",
        b"Infinity",
        b"1e9999",
        b"{}\x00ignored",
        b'"\\u0000"',
        b'"\\ud800"',
        b'"\xff"',
        b"[" * 2000 + b"]" * 2000,
    ],
)
def test_finite_json_ingress_refuses_ambiguous_or_unrepresentable_values(content):
    with pytest.raises(JsonBoundaryError):
        finite_json_loads(content)


def test_finite_interchange_owns_numbers_without_changing_scope_identity():
    expected = {"whole": 9007199254740993, "fraction": 1.25, "flag": True, "empty": None}
    assert finite_json_loads(finite_json_bytes(expected)) == expected
    assert finite_json_loads(b"1e2") == 100.0
    assert type(finite_json_loads(b"1")) is int
    assert type(finite_json_loads(b"1.0")) is float
    assert json_bytes(json_loads(PRECISE)) == PRECISE


@pytest.mark.parametrize("value", [float("inf"), Decimal("1.25"), {1: "one"}, (1, 2)])
def test_finite_json_egress_requires_the_declared_inert_domain(value):
    with pytest.raises(JsonBoundaryError):
        finite_json_bytes(value)


def test_scope_json_keeps_fractional_digits_through_context_and_frozen_demand():
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
    from semantic.data_operation_declaration_support import model, operation

    scope = SubjectContext("project", "subject", "original", PRECISE, subject_definition="document")
    assert scope.analyzed_scope == PRECISE
    assert scope.record["analyzed_scope"] == {
        "coordinate": Decimal("0.12345678901234567890123456789"),
        "page": 1,
    }
    intent = freeze_demand(
        model(operation("op:result")),
        roots=(RootSubject("subject", "original", PRECISE),),
        targets=("op:result",),
        inference="exact",
        execution_profile="one",
    )
    assert PRECISE in intent.content
    assert json_bytes(intent.record["roots"][0]["analyzed_scope"]) == PRECISE
    nearby = SubjectContext(
        "project",
        "subject",
        "original",
        PRECISE.replace(b"6789,", b"6790,"),
        subject_definition="document",
    )
    assert scope != nearby
    assert SemanticRequestKey(
        "recipe", "subject", {}, {}, "exact", subject_context=scope
    ).identity.key != (
        SemanticRequestKey(
            "recipe", "subject", {}, {}, "exact", subject_context=nearby
        ).identity.key
    )


def test_wire_snapshot_keeps_only_scope_numbers_exact_and_preserves_typed_meaning():
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
    from semantic.data_operation_declaration_support import model, operation

    intent = freeze_demand(
        model(operation("op:result")),
        roots=(RootSubject("subject", "original", PRECISE),),
        targets=("op:result",),
        inference="exact",
        execution_profile="one",
    )
    payload = {
        "project_id": "project:one",
        "release_id": "release:one",
        "runtime_id": "runtime:one",
        "root": intent.record["roots"],
        "selection": intent.record,
        "strength": "value",
    }
    checked = validate_native_wire("register_data_demand", "input", payload)
    assert json_bytes(checked["root"][0]["analyzed_scope"]) == PRECISE
    assert json_bytes(checked["selection"]["roots"][0]["analyzed_scope"]) == PRECISE
    value = wire_json_loads(b'{"analyzed_scope":{"x":0.1234567890123456789},"body":1.25}')
    assert value["analyzed_scope"]["x"] == Decimal("0.1234567890123456789")
    assert type(value["body"]) is float
    assert semantic_value(value["body"]) == ["float", "0x1.4000000000000p+0"]
    assert semantic_value(Decimal("1.25")) == ["decimal", "1.25"]


@pytest.mark.parametrize("invalid", [float("inf"), Decimal("NaN"), {"scope": float("nan")}])
def test_exact_json_refuses_nonfinite_numbers(invalid):
    with pytest.raises(ValueError):
        json_bytes(invalid)


@pytest.mark.db
def test_native_jsonb_preserves_fraction_and_context_key_meaning(native_rollback):
    from corpus_structure.semantic.data_operation_value_native import data_operation_value_sql
    from semantic.native_program_support import routine_declaration

    helper = routine_declaration(data_operation_value_sql(), "data", "ddo_json_meaning")
    connection = native_rollback.connection
    connection.exec_driver_sql(helper)
    # The production DDO column binder/result type crosses actual JSONB.
    result = connection.scalar(
        select(
            cast(
                bindparam("scope", type_=ContextJSONB()),
                ContextJSONB(),
            )
        ),
        {"scope": json_loads(PRECISE)},
    )
    assert json_bytes(result) == PRECISE
    expected = [
        "mapping",
        [
            ["coordinate", ["decimal", "0.12345678901234567890123456789"]],
            ["page", ["decimal", "1"]],
        ],
    ]
    assert (
        connection.scalar(
            text("SELECT pg_temp.ddo_json_meaning(CAST(:scope AS jsonb))"),
            {"scope": json_bytes(result).decode()},
        )
        == expected
    )
    context = SubjectContext(
        "project", "subject", "original", json_bytes(result), subject_definition="document"
    )
    assert semantic_value(context.identity_record)[1][0] == ["analyzed_scope", expected]


@pytest.mark.parametrize(
    "kind,value,expected",
    [
        ("digest", "a" * 64, True),
        ("digest", "a" * 64 + "\n", False),
        ("digest", "a" * 63, False),
        ("integer", ["integer", "-12"], True),
        ("integer", ["integer", "-12\n"], False),
        ("decimal", ["decimal", "1.25e-3"], True),
        ("decimal", ["decimal", "1.25e-3\n"], False),
        ("advisory-date", "2026-11-21", True),
        ("advisory-date", "not-a-date", True),
    ],
)
def test_declared_portable_patterns_match_native_at_true_input_end(
    native_rollback, kind, value, expected
):
    import json

    import yaml
    from jsonschema import ValidationError
    from sqlalchemy import JSON, func

    from corpus_structure.model.compiled import model_source
    from corpus_structure.semantic.data_operation_wire import (
        DRAFT7,
        generated_json_schema,
        schema_closure,
    )
    from corpus_structure.semantic.schema_validation import prepared_schema_validator

    if kind == "advisory-date":
        schema = generated_json_schema({"type": "string", "format": "date"})
        assert schema["x-ddo-format"] == "date"
        assert "format" not in schema
    else:
        definitions = yaml.safe_load(model_source("data-operation-native.yaml"))["definitions"]
        name = "pdf_search_digest" if kind == "digest" else "semantic_value"
        schema = {
            "$schema": DRAFT7,
            **schema_closure({"$ref": "#/definitions/" + name}, definitions),
        }
    encoded = json.dumps(schema).encode()
    validator = prepared_schema_validator(encoded)
    if expected:
        validator.validate(value)
    else:
        with pytest.raises(ValidationError):
            validator.validate(value)
    native = native_rollback.connection.scalar(
        select(
            func.public.json_matches_schema(
                cast(bindparam("schema"), JSON), cast(bindparam("value"), JSON)
            )
        ),
        {"schema": encoded.decode(), "value": json.dumps(value)},
    )
    assert native is expected


def test_linkml_digest_type_preserves_full_input_pattern_in_generated_schema():
    import json

    import yaml
    from jsonschema.validators import validator_for
    from linkml.generators.jsonschemagen import JsonSchemaGenerator
    from linkml_runtime.linkml_model import SchemaDefinition
    from linkml_runtime.utils.schemaview import SchemaView

    from corpus_structure.model.compiled import model_source

    declaration = yaml.safe_load(model_source("pdf-products.yaml"))
    schema = SchemaDefinition(
        id="https://example.org/pattern",
        name="pattern",
        prefixes={
            "xsd": {
                "prefix_prefix": "xsd",
                "prefix_reference": "http://www.w3.org/2001/XMLSchema#",
            },
            "p": {"prefix_prefix": "p", "prefix_reference": "https://example.org/pattern/"},
        },
        default_prefix="p",
        types={"Digest": declaration["types"]["PdfDigest"]},
        classes={"Record": {"attributes": {"digest": {"range": "Digest", "required": True}}}},
    )
    view = SchemaView(schema)
    generated = json.loads(
        JsonSchemaGenerator(schema, schemaview=view, top_class="Record").serialize()
    )
    validator = validator_for(generated)(generated)
    assert validator.is_valid({"digest": "a" * 64})
    assert not validator.is_valid({"digest": "a" * 64 + "\n"})
