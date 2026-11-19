"""SQL-standard bodies are declared directly and bind their actual dependencies."""

from dataclasses import replace

import pytest
from pglast import ast, parse_sql
from sqlalchemy import Column, Integer, MetaData, Table, select, text
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.native_program import (
    Block,
    NativeRoutine,
    Parameter,
    core_variable,
    pg_type,
)


def test_sql_standard_select_keeps_typed_envelope_and_refuses_procedural_or_nonselect():
    routine = NativeRoutine(
        "ops",
        "selected_value",
        (Parameter("p_value", pg_type("int4")),),
        pg_type("int4"),
        select(core_variable("p_value", Integer())),
        sql_standard=True,
    )
    assert routine.render() == (
        "CREATE OR REPLACE FUNCTION ops.selected_value(p_value integer) RETURNS integer "
        "LANGUAGE sql BEGIN ATOMIC SELECT p_value; END"
    )
    statement = parse_sql(routine.render())[0].stmt
    assert isinstance(statement, ast.CreateFunctionStmt)
    assert statement.sql_body is not None and statement.options is not None
    assert not any(option.defname == "as" for option in statement.options)
    for body in (Block(()), ast.DeleteStmt(relation=ast.RangeVar(relname="unbound"))):
        with pytest.raises(ValueError, match="structured SELECT"):
            replace(routine, body=body).render()


def test_sql_standard_routine_executes_and_retains_server_bound_relation(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    source = Table("selected_source", MetaData(), Column("value", Integer), schema="ops")
    connection.execute(CreateTable(source))
    connection.execute(source.insert(), [{"value": 17}])
    routine = NativeRoutine(
        "ops",
        "selected_source_value",
        (),
        pg_type("int4"),
        select(source.c.value),
        sql_standard=True,
    )
    execute_native_sql(connection, routine.render())
    assert connection.scalar(text("SELECT ops.selected_source_value()")) == 17
    connection.exec_driver_sql("ALTER TABLE ops.selected_source RENAME TO renamed_source")
    assert connection.scalar(text("SELECT ops.selected_source_value()")) == 17
    assert "renamed_source" in connection.scalar(
        text("SELECT pg_get_functiondef('ops.selected_source_value()'::regprocedure)")
    )
