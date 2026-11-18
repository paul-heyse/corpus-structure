"""Actual dynamic relation scanning keeps identifiers and values distinct."""

from sqlalchemy import column, text

from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.native_program import (
    Assign,
    Block,
    ForRelation,
    Local,
    Parameter,
    Return,
    core_variable,
    function,
    literal,
    pg_type,
    variable,
)


def test_model_owned_dynamic_scan_quotes_percent_and_relation_names(semantic_bare_engine):
    from sqlalchemy import BigInteger

    value = core_variable("value_", BigInteger())
    total = core_variable("total_", BigInteger())
    sql = function(
        "checker_test",
        "sum_uploaded",
        parameters=(Parameter("incoming", pg_type("regclass")),),
        returns=pg_type("bigint"),
        body=Block(
            (
                ForRelation(
                    ("value_",),
                    ("number%quoted",),
                    variable("incoming"),
                    (column("number%quoted"),),
                    (Assign("total_", total + value),),
                ),
                Return(total),
            ),
            (
                Local("total_", pg_type("bigint"), literal(0)),
                Local("value_", pg_type("bigint")),
            ),
        ),
        search_path=("pg_catalog", "pg_temp"),
    )
    with semantic_bare_engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA checker_test")
        execute_native_sql(connection, 'CREATE TEMP TABLE "incoming % uploads" ("number%quoted" bigint)')
        execute_native_sql(connection, 'INSERT INTO "incoming % uploads" VALUES (9),(2),(4)')
        execute_native_sql(connection, sql)
        assert connection.scalar(
            text("SELECT checker_test.sum_uploaded(CAST(:relation AS regclass))"),
            {"relation": 'pg_temp."incoming % uploads"'},
        ) == 15
