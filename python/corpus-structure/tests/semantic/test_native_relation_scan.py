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


def test_model_owned_dynamic_scan_quotes_percent_and_relation_names(infrastructure_rollback):
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
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA checker_test")
    execute_native_sql(
        connection, 'CREATE TEMP TABLE "incoming % uploads" ("number%quoted" bigint)'
    )
    execute_native_sql(connection, 'INSERT INTO "incoming % uploads" VALUES (9),(2),(4)')
    execute_native_sql(connection, sql)
    assert (
        connection.scalar(
            text("SELECT checker_test.sum_uploaded(CAST(:relation AS regclass))"),
            {"relation": 'pg_temp."incoming % uploads"'},
        )
        == 15
    )


def test_postgresql_perform_query_executes_every_selected_effect_row(infrastructure_rollback):
    from sqlalchemy import cast, func, select
    from sqlalchemy import literal as sql_literal
    from sqlalchemy.dialects.postgresql import REGCLASS

    from corpus_structure.semantic.native_program import PerformQuery

    rows = func.generate_series(1, 3).table_valued("ordinal")
    query = select(
        func.nextval(cast(sql_literal("pg_temp.effect_counter"), REGCLASS()))
    ).select_from(rows)
    program = function(
        "checker_test",
        "consume_rows",
        parameters=(),
        returns=pg_type("void"),
        body=Block((PerformQuery(query),)),
        search_path=("pg_catalog", "pg_temp"),
    )
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA checker_test")
    connection.exec_driver_sql("CREATE TEMP SEQUENCE effect_counter")
    execute_native_sql(connection, program)
    connection.execute(text("SELECT checker_test.consume_rows()")).one()
    assert connection.scalar(text("SELECT last_value FROM pg_temp.effect_counter")) == 3
