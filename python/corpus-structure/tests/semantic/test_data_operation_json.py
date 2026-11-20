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
    wire_json_loads,
)
from corpus_structure.semantic.data_operation_jsonb import ContextJSONB
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_operation_wire import validate_native_wire

PRECISE = b'{"coordinate":0.12345678901234567890123456789,"page":1}'


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
