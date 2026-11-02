import pytest
from pglast import ast
from sqlalchemy import Column, MetaData, Table, Text

from corpus_structure.semantic.authored_sql import SQLAdmissionError, _syntax
from corpus_structure.semantic.prepared_sql import SQLSyntaxError, prepare_sql


def test_source_slices_mutation_ownership_and_changed_source():
    source = " -- Ω\n SELECT 'x;y';  SELECT $$a;b$$;\n"
    prepared = prepare_sql(source, source="literal.sql")
    assert prepared.sql == source
    assert prepared.excerpt(0) == "-- Ω\n SELECT 'x;y'"
    assert prepared.excerpt(1) == "SELECT $$a;b$$"
    private = prepared.private_tree()
    private_select = private[0].stmt
    shared_select = prepared.statements[0].stmt
    assert isinstance(private_select, ast.SelectStmt) and isinstance(shared_select, ast.SelectStmt)
    assert private_select.targetList and shared_select.targetList
    private_value = private_select.targetList[0].val
    shared_value = shared_select.targetList[0].val
    assert isinstance(private_value, ast.A_Const) and isinstance(shared_value, ast.A_Const)
    assert isinstance(private_value.val, ast.String) and isinstance(shared_value.val, ast.String)
    private_value.val.sval = "changed"
    assert shared_value.val.sval == "x;y"
    assert prepared.digest != prepare_sql(source.replace("x;y", "z")).digest
    assert isinstance(private[0], ast.RawStmt)


def test_unicode_error_coordinates_and_unknown_span():
    with pytest.raises(SQLSyntaxError) as error:
        prepare_sql("SELECT 'Ω'; SELLECT 1", source="broken.sql")
    # Preserve the pinned parser's reported index; do not convert it a second time.
    # Its error cursor is one character before SELLECT in this Unicode case.
    assert error.value.position == 11
    assert error.value.excerpt == "SELECT 'Ω'; SELLECT 1"
    assert "broken.sql" in str(error.value)
    assert SQLSyntaxError("x", "Ω", "missing", None).excerpt is None


def test_sql_standard_body_slices_preserve_nested_semicolons_and_unicode():
    source = (
        "-- Ω\nCREATE FUNCTION x() RETURNS text LANGUAGE sql "
        "BEGIN ATOMIC SELECT 'é;'; END; SELECT 'after';"
    )
    prepared = prepare_sql(source, source="sql-standard.sql")
    assert len(prepared.statements) == len(prepared.slices) == 2
    assert prepared.excerpt(0) == (
        "CREATE FUNCTION x() RETURNS text LANGUAGE sql BEGIN ATOMIC SELECT 'é;'; END"
    )
    assert prepared.excerpt(1) == "SELECT 'after'"
    for index in range(2):
        assert len(prepare_sql(prepared.excerpt(index)).statements) == 1


def test_prepared_authored_consumer_nested_ctes_and_forbidden_descendant():
    md = MetaData()
    Table("entity", md, Column("value", Text), schema="data")
    query = prepare_sql(
        "WITH RECURSIVE t AS (SELECT * FROM data.entity UNION ALL SELECT * FROM t) SELECT * FROM t",
        source="cte.sql",
    )
    assert _syntax(query, md) == (("data.entity",), ())
    with pytest.raises(SQLAdmissionError, match="unapproved function") as error:
        _syntax(prepare_sql("SELECT 'Ω', (SELECT pg_catalog.pg_sleep(1))", source="unsafe.sql"), md)
    assert error.value.location == len("SELECT 'Ω', (SELECT ")
