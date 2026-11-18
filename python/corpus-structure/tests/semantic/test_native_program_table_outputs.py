"""Actual PostgreSQL grammar for generated table-output parameter names."""

import pytest
from pglast import parse_sql
from pglast.stream import RawStream
from sqlalchemy import BigInteger, case, cast, literal, select, text

from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.native_program import (
    Block,
    If,
    Return,
    ReturnQuery,
    function,
    pg_type,
    sql_function,
)


@pytest.mark.parametrize("language", ["sql", "plpgsql"])
def test_table_output_position_uses_contextual_identifier_quoting(semantic_bare_engine, language):
    returns = pg_type("record")
    returns.setof = True
    query = select(cast(literal(7), BigInteger()), literal("retained"))
    options = dict(
        parameters=(),
        returns=returns,
        table_columns=(("position", pg_type("bigint")), ("value", pg_type("text"))),
    )
    program = (
        sql_function("public", "typed_table_output", body=query, **options)
        if language == "sql"
        else function("public", "typed_table_output", body=Block((ReturnQuery(query),)), **options)
    )
    assert '"position" bigint' in program
    with semantic_bare_engine.begin() as connection:
        execute_native_sql(connection, program)
        assert connection.execute(text("SELECT * FROM public.typed_table_output()")).one() == (
            7,
            "retained",
        )


def test_unambiguous_table_output_retains_native_printer_bytes():
    returns = pg_type("record")
    returns.setof = True
    program = sql_function(
        "public",
        "typed_table_output",
        parameters=(),
        returns=returns,
        table_columns=(("ordinal", pg_type("bigint")),),
        body=select(literal(7)),
    )
    statement = parse_sql(program)[0].stmt
    assert statement is not None
    assert RawStream()(statement) == program


def test_case_then_remains_inside_procedural_condition(semantic_bare_engine):
    condition = literal("matched").is_distinct_from(
        case((literal(False), "other"), else_="matched")
    )
    program = function(
        "public",
        "typed_nested_condition",
        parameters=(),
        returns=pg_type("bool"),
        body=Block((If(condition, (Return(literal(False)),)), Return(literal(True)))),
    )
    with semantic_bare_engine.begin() as connection:
        execute_native_sql(connection, program)
        assert connection.scalar(text("SELECT public.typed_nested_condition()")) is True
