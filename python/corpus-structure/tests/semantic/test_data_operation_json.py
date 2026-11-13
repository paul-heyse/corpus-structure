"""Exact scope JSON; independent literals retain fractional context meaning."""

from decimal import Decimal
from importlib.resources import files

import pytest
from sqlalchemy import bindparam, cast, select, text

from corpus_structure.semantic.data_operation_identity import SemanticRequestKey, semantic_value
from corpus_structure.semantic.data_operation_json import (
    ContextJSONB,
    json_bytes,
    json_loads,
    wire_json_loads,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_wire import validate_native_wire

PRECISE = b'{"coordinate":0.12345678901234567890123456789,"page":1}'


def test_scope_json_keeps_fractional_digits_through_context_and_frozen_demand():
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand

    from .test_data_operation_demands import model, operation

    scope = SubjectContext("project", "subject", "original", PRECISE)
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
    nearby = SubjectContext("project", "subject", "original", PRECISE.replace(b"6789,", b"6790,"))
    assert scope != nearby
    assert SemanticRequestKey(
        "recipe", "subject", {}, {}, "exact", subject_context=scope
    ).identity.key != (
        SemanticRequestKey(
            "recipe", "subject", {}, {}, "exact", subject_context=nearby
        ).identity.key
    )


def test_wire_snapshot_keeps_only_scope_numbers_exact_and_preserves_typed_meaning():
    payload = {
        "demand_id": "demand:one",
        "operation_id": "op:one",
        "subject": "subject",
        "original_source": "original",
        "analyzed_scope": json_loads(PRECISE),
        "parameters": {"untyped-display": 1.25},
    }
    checked = validate_native_wire("expand_data_obligation", "input", payload)
    assert json_bytes(checked["analyzed_scope"]) == PRECISE
    assert type(checked["parameters"]["untyped-display"]) is float
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
def test_native_jsonb_preserves_fraction_and_context_key_meaning(semantic_db_engine):
    source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
    start = source.index("CREATE OR REPLACE FUNCTION data.ddo_json_meaning(")
    end = source.index("CREATE OR REPLACE FUNCTION data.ddo_identity(", start)
    helper = source[start:end].replace("data.ddo_json_meaning", "pg_temp.ddo_json_meaning")
    with semantic_db_engine.connect() as connection:
        transaction = connection.begin()
        try:
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
            context = SubjectContext("project", "subject", "original", json_bytes(result))
            assert semantic_value(context.identity_record)[1][0] == ["analyzed_scope", expected]
        finally:
            transaction.rollback()
