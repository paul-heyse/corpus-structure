"""Native private guard compilation/refusals, separate from full grade journeys."""

import json

import pytest
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import metadata, table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.record_grade_native import record_grade_native_sql
from corpus_structure.semantic.data_operation_projections import (
    compiled, cut_selection_projection, read_page, selected_support_output,
)


def compiled_grade_sql():
    from corpus_structure.semantic.data_operation_projections import capture_projection_sources
    sources = capture_projection_sources()
    products = json.loads(next(source.content for source in sources if source.name == 'native/data-operation-projections.json'))
    return record_grade_native_sql().replace(
        "__DDO_CORE_RECORD_GRADE_CENSUS_NODES__", products['record_grade_census_nodes'],
    ).replace("__DDO_CORE_RECORD_GRADE_CENSUS_SCOPES__", products['record_grade_census_scopes']).replace(
        "__DDO_CORE_CUT_SELECTION__", compiled(cut_selection_projection()),
    ).replace("__DDO_CORE_READ_PAGE__", compiled(read_page(metadata))).replace("__DDO_CORE_SELECTED_SUPPORT_OUTPUT__", compiled(selected_support_output(metadata)))


@pytest.fixture
def grade_guard_connection(semantic_bare_engine):
    # Real current physical composite types, no fake producer, publication or CPU
    # receipt. This compiles private PL/pgSQL and tests early closed refusals only.
    required = ('ops.data_request', 'ops.data_demand', 'ops.data_demand_read',
                'ops.data_derivation', 'sem.data_operation_definition')
    with semantic_bare_engine.begin() as connection:
        for schema in ('ops', 'sem', 'data', 'kb'):
            connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS {schema}')
        for name in required:
            connection.execute(CreateTable(table(name), include_foreign_key_constraints=[]))
        sql = compiled_grade_sql()
        assert '__DDO_CORE_' not in sql
        connection.exec_driver_sql(sql, execution_options={'no_parameters': True})
        yield connection


def test_native_grade_helpers_are_private_and_closed(grade_guard_connection):
    connection = grade_guard_connection
    request = json.dumps({'operation_id': 'unrelated.operation', 'project_id': 'unrelated-project'})
    assert connection.scalar(text('SELECT count(*) FROM ops.ddo_record_grade_completion_scopes(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)))'), {'r': request}) == 0
    connection.execute(text('SELECT ops.ddo_require_record_grade_completion(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)),CAST(:completion AS jsonb))'), {'r': request, 'completion': '{}'})
    assert connection.scalar(text("SELECT ops.ddo_record_grade_dependencies_valid('missing-episode')")) is False
    public_functions = connection.scalar(text("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='ops' AND p.proname LIKE '%record_grade%' AND EXISTS(SELECT FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) grant_ WHERE grant_.grantee=0 AND grant_.privilege_type='EXECUTE')"))
    assert public_functions == 0


def test_native_grade_scope_refuses_missing_project_or_retained_cut(grade_guard_connection):
    with pytest.raises(DBAPIError):
        grade_guard_connection.execute(text("SELECT * FROM ops.ddo_record_grade_cut_scopes('actual-project',:cut)"), {'cut': '{"project_id":"foreign-project","demand_id":"missing","read_id":"missing"}'})


def test_native_grade_function_population_has_independent_expected_signatures():
    statements = prepare_sql(record_grade_native_sql(), source='record-grade-native').statements
    names = {statement.stmt.funcname[-1].sval for statement in statements if isinstance(statement.stmt, ast.CreateFunctionStmt) and statement.stmt.funcname}
    assert names == {
        'ddo_record_grade_input_value', 'ddo_record_grade_input', 'ddo_record_grade_require_finite_census',
        'ddo_record_grade_cut_scopes', 'ddo_record_grade_require_cut', 'ddo_record_grade_census_row', 'ddo_record_grade_require_source',
        'ddo_record_grade_completion_scopes', 'ddo_record_grade_dependency_scopes',
        'ddo_record_grade_require_frame', 'ddo_require_record_grade_completion', 'ddo_record_grade_dependencies_valid',
    }
