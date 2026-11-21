"""Pinned public eligibility precedes independently refusing capability controls."""

import json

import psycopg
import pytest
from sqlalchemy import Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_projections import (
    _disclosed_body_access,
    _disclosed_kind_access,
    _selected_support_output_rows,
)
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.native_program import (
    Block,
    Parameter,
    Return,
    core_variable,
    function,
    pg_type,
)


@pytest.fixture
def disclosure_control(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA sem")
    connection.exec_driver_sql("CREATE SCHEMA ops")
    connection.exec_driver_sql(
        "CREATE TABLE sem.data_kind_contract(kind_contract text PRIMARY KEY,universe text)"
    )
    connection.exec_driver_sql(
        "INSERT INTO sem.data_kind_contract VALUES "
        "('ordinary','ordinary'),('source','source'),('protected','evaluator')"
    )
    connection.exec_driver_sql("CREATE TABLE pg_temp.disclosure_cut(public_disclosure boolean)")
    # These ports deliberately raise, rather than return false, on missing caller
    # authority. They isolate SQL execution order; the native journeys own actual
    # role/universe and recursive member-body authorization qualification.
    connection.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_kind_access(kind text) RETURNS boolean LANGUAGE plpgsql STABLE "
        "AS $$BEGIN IF kind='unknown' OR (kind='protected' AND "
        "current_setting('test.disclosure_evaluator',true) IS DISTINCT FROM 'on') THEN "
        "RAISE EXCEPTION 'controlled kind refusal' USING ERRCODE='42501'; END IF; "
        "RETURN true; END$$"
    )
    connection.exec_driver_sql(
        "CREATE FUNCTION ops.ddo_body_access(kind text,body jsonb) RETURNS boolean "
        "LANGUAGE plpgsql STABLE AS $$BEGIN PERFORM ops.ddo_kind_access(kind); "
        "IF body->>'protected_member'='true' AND "
        "current_setting('test.disclosure_evaluator',true) IS DISTINCT FROM 'on' THEN "
        "RAISE EXCEPTION 'controlled member refusal' USING ERRCODE='42501'; END IF; "
        "RETURN true; END$$"
    )
    kind, body = core_variable("kind", Text()), core_variable("body", JSONB())
    for name, expression in (
        ("disclosed_kind", _disclosed_kind_access(get_metadata(), kind)),
        ("disclosed_body", _disclosed_body_access(get_metadata(), kind, body)),
    ):
        execute_native_sql(
            connection,
            function(
                "pg_temp",
                name,
                parameters=(
                    Parameter("boundary", pg_type("pg_temp", "disclosure_cut")),
                    Parameter("kind", pg_type("text")),
                    Parameter("body", pg_type("jsonb")),
                ),
                returns=pg_type("bool"),
                body=Block((Return(expression),)),
                search_path=("pg_catalog", "pg_temp"),
            ),
        )
    return connection


def _access(connection, kind, *, public, body=None, body_check=False):
    return connection.scalar(
        text(
            "SELECT pg_temp."
            + ("disclosed_body" if body_check else "disclosed_kind")
            + "(ROW(:public)::pg_temp.disclosure_cut,:kind,CAST(:body AS jsonb))"
        ),
        dict(public=public, kind=kind, body=json.dumps({} if body is None else body)),
    )


@pytest.mark.parametrize("body_check", [False, True])
def test_public_hidden_kind_does_not_execute_refusing_authorization(disclosure_control, body_check):
    connection = disclosure_control
    for kind, expected in (
        ("ordinary", True),
        ("source", True),
        ("protected", False),
        ("unknown", False),
    ):
        assert _access(connection, kind, public=True, body_check=body_check) is expected
    connection.execute(text("SELECT set_config('test.disclosure_evaluator','on',true)"))
    # Reopening the same public disclosure with evaluator capability cannot make
    # its withheld protected kind eligible.
    assert _access(connection, "protected", public=True, body_check=body_check) is False


@pytest.mark.parametrize("body_check", [False, True])
def test_full_cut_keeps_live_caller_authorization(disclosure_control, body_check):
    connection = disclosure_control
    with (
        pytest.raises(DBAPIError, match="controlled kind refusal") as error,
        connection.begin_nested(),
    ):
        _access(connection, "protected", public=False, body_check=body_check)
    assert isinstance(error.value.orig, psycopg.Error)
    assert error.value.orig.sqlstate == "42501"
    connection.execute(text("SELECT set_config('test.disclosure_evaluator','on',true)"))
    assert _access(connection, "protected", public=False, body_check=body_check) is True


def test_disclosed_ordinary_body_still_refuses_a_protected_nested_member(disclosure_control):
    connection = disclosure_control
    with (
        pytest.raises(DBAPIError, match="controlled member refusal") as error,
        connection.begin_nested(),
    ):
        _access(
            connection, "ordinary", public=True, body={"protected_member": True}, body_check=True
        )
    assert isinstance(error.value.orig, psycopg.Error)
    assert error.value.orig.sqlstate == "42501"


def test_support_export_only_authorizes_publicly_disclosed_product_bodies(disclosure_control):
    from sqlalchemy import select

    from corpus_structure.semantic.data_operation_projections import _support_export_body_access

    connection = disclosure_control
    connection.exec_driver_sql("CREATE SCHEMA kb")
    connection.exec_driver_sql(
        "CREATE TABLE kb.data_product(id text PRIMARY KEY,kind_contract text,canonical_body jsonb)"
    )
    connection.exec_driver_sql(
        "INSERT INTO kb.data_product VALUES ('visible','ordinary','{}'),('hidden','protected','{}')"
    )
    metadata = get_metadata()
    products = metadata.tables["kb.data_product"]
    selected = select(products.c.id.label("product_id")).cte("test_selected_products")
    execute_native_sql(
        connection,
        function(
            "pg_temp",
            "disclosed_support_bodies",
            parameters=(Parameter("boundary", pg_type("pg_temp", "disclosure_cut")),),
            returns=pg_type("bool"),
            body=Block((Return(_support_export_body_access(metadata, products, selected)),)),
            search_path=("pg_catalog", "pg_temp"),
        ),
    )

    def authorize(*, public):
        return connection.scalar(
            text("SELECT pg_temp.disclosed_support_bodies(ROW(:public)::pg_temp.disclosure_cut)"),
            {"public": public},
        )

    assert authorize(public=True) is True
    with (
        pytest.raises(DBAPIError, match="controlled kind refusal"),
        connection.begin_nested(),
    ):
        authorize(public=False)
    connection.exec_driver_sql(
        "UPDATE kb.data_product SET canonical_body = '{\"protected_member\":true}' WHERE id='visible'"
    )
    with (
        pytest.raises(DBAPIError, match="controlled member refusal"),
        connection.begin_nested(),
    ):
        authorize(public=True)


def test_selected_output_authorization_is_inside_exact_reached_public_support():
    from pglast import ast, parse_sql
    from sqlalchemy.dialects.postgresql import dialect

    query = _selected_support_output_rows(get_metadata())
    source = str(query.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
    parsed = parse_sql(source)[0].stmt
    assert isinstance(parsed, ast.SelectStmt)
    # Immutable support/project/shape eligibility is the outer CASE. A separate
    # SQL AND predicate could be reordered ahead of those bounds by PostgreSQL.
    assert isinstance(parsed.whereClause, ast.CaseExpr) and parsed.whereClause.args
    assert isinstance(parsed.whereClause.args[0].result, ast.CaseExpr)
    assert "boundary.public_disclosure" in source
    assert "ddo_policy_authority_leaf" in source
    assert "support_closure.kind IN ('episode', 'authority')" in source
    feature = _selected_support_output_rows(get_metadata(), purpose="feature-fit")
    feature_source = str(feature.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
    assert "ddo_feature_fit_body_access" in feature_source
    assert "ddo_structural_report_support" not in feature_source


def test_custody_output_keeps_exact_disclosure_and_pinned_nested_universes():
    from pglast import ast, parse_sql
    from sqlalchemy.dialects.postgresql import dialect

    from corpus_structure.semantic.data_operation_projections import selected_support_output

    query = _selected_support_output_rows(get_metadata(), purpose="custody")
    source = str(query.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
    parsed = parse_sql(source)[0].stmt
    assert isinstance(parsed, ast.SelectStmt)
    assert isinstance(parsed.whereClause, ast.CaseExpr)
    for required in (
        "boundary.public_disclosure",
        "boundary.access_universes",
        "ops.ddo_body_kind_contracts",
        "ops.ddo_policy_authority_leaf",
        "ops.ddo_valid_closure",
        "selected_uses.id = p_use",
        "kb.data_product.project_id = d.project_id",
        "ops.data_derivation_output.member_id IS NULL",
        "support_closure.kind IN ('episode', 'authority')",
        "coalesce(boundary.access_universes ? sem.data_kind_contract.universe, false)",
    ):
        assert required in source
    assert "ddo_body_access" not in source
    assert "ddo_kind_access" not in source
    assert "ddo_feature_fit_body_access" not in source
    assert {item.name for item in query.selected_columns} == {"derivation_id", "product_id"}
    selected = selected_support_output(get_metadata(), purpose="custody")
    selected_source = str(
        selected.compile(dialect=dialect(), compile_kwargs={"literal_binds": True})
    )
    assert "selected_whole_outputs.derivation_id = p_derivation" in selected_source
    assert "selected_whole_outputs.product_id = p_product" in selected_source
