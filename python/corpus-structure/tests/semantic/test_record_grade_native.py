"""Native private guard compilation/refusals, separate from full grade journeys."""

import json
from hashlib import sha256

import pytest
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import metadata, table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.record_grade_native import record_grade_native_sql


@pytest.fixture
def grade_guard_connection(infrastructure_rollback):
    # Real current physical composite types, no fake producer, publication or CPU
    # receipt. This compiles private PL/pgSQL and tests early closed refusals only.
    required = (
        "ops.data_request",
        "ops.data_demand",
        "ops.data_demand_read",
        "ops.data_derivation",
        "ops.data_completion_intent",
        "sem.data_operation_definition",
        "sem.artifact",
        "sem.release_finalization",
    )
    connection = infrastructure_rollback
    for schema in ("ops", "sem", "data", "kb"):
        connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    for name in required:
        connection.execute(CreateTable(table(name), include_foreign_key_constraints=[]))
    sql = record_grade_native_sql(metadata)
    assert "__DDO_CORE_" not in sql
    connection.exec_driver_sql(sql, execution_options={"no_parameters": True})
    yield connection


def test_program_grade_helpers_are_private_and_closed(grade_guard_connection):
    connection = grade_guard_connection
    request = json.dumps({"operation_id": "unrelated.operation", "project_id": "unrelated-project"})
    assert (
        connection.scalar(
            text(
                "SELECT count(*) FROM ops.ddo_record_grade_completion_scopes(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)))"
            ),
            {"r": request},
        )
        == 0
    )
    connection.execute(
        text(
            "SELECT ops.ddo_require_record_grade_completion(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)),CAST(:completion AS jsonb))"
        ),
        {"r": request, "completion": "{}"},
    )
    assert (
        connection.scalar(text("SELECT ops.ddo_record_grade_dependencies_valid('missing-episode')"))
        is False
    )
    public_functions = connection.scalar(
        text(
            "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='ops' AND p.proname LIKE '%record_grade%' AND EXISTS(SELECT FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) grant_ WHERE grant_.grantee=0 AND grant_.privilege_type='EXECUTE')"
        )
    )
    assert public_functions == 0


def test_program_grade_scope_refuses_missing_project_or_retained_cut(grade_guard_connection):
    with pytest.raises(DBAPIError):
        grade_guard_connection.execute(
            text("SELECT * FROM ops.ddo_record_grade_cut_scopes('actual-project',:cut)"),
            {"cut": '{"project_id":"foreign-project","demand_id":"missing","read_id":"missing"}'},
        )


def test_native_class_contract_requires_one_complete_owner_in_the_finalized_archive(
    grade_guard_connection,
):
    connection = grade_guard_connection
    archive = table("sem.artifact")
    finalized = table("sem.release_finalization")
    release = "release:class-contract-fixture"
    kind = {
        "semantic_id": "urn:fixture:reading",
        "name": "Reading",
        "category": "class",
        "complete": True,
    }
    identity = {"owner": kind["semantic_id"], "key": "kind:reading", "domain": "kind"}
    body = {"kinds": [kind], "identities": [identity]}

    def encoded(value):
        content = json.dumps(value).encode()
        return {"content": content, "content_digest": sha256(content).hexdigest()}

    query = text("SELECT sem.ddo_model_class_contract(:release,:contract,:name)")

    def matches(name=None, contract="kind:reading"):
        return connection.scalar(query, {"release": release, "contract": contract, "name": name})

    connection.execute(
        archive.insert().values(
            release_id=release,
            artifact_name="data_operations.json",
            media_type="application/json",
            **encoded(body),
        )
    )
    assert matches() is False
    connection.execute(finalized.insert().values(release_id=release, content_digest="a" * 64))
    assert matches() is True
    assert matches("Reading") is True
    assert matches("Other") is False
    assert matches(contract="kind:other") is False
    for invalid in (
        body | {"kinds": [kind, kind]},
        body | {"kinds": [kind | {"complete": False}]},
        body | {"kinds": [kind | {"category": "slot"}]},
        body | {"identities": [identity, identity]},
        body | {"identities": [identity | {"owner": "urn:fixture:other"}]},
    ):
        connection.execute(
            archive.update().where(archive.c.release_id == release).values(**encoded(invalid))
        )
        assert matches() is False


def test_program_grade_function_population_has_independent_expected_signatures():
    statements = prepare_sql(
        record_grade_native_sql(metadata), source="record-grade-native"
    ).statements
    names = {
        statement.stmt.funcname[-1].sval
        for statement in statements
        if isinstance(statement.stmt, ast.CreateFunctionStmt) and statement.stmt.funcname
    }
    assert names == {
        "ddo_model_class_contract",
        "ddo_record_grade_input_value",
        "ddo_record_grade_input",
        "ddo_record_grade_require_finite_census",
        "ddo_record_grade_cut_scopes",
        "ddo_record_grade_require_cut",
        "ddo_record_grade_acquire_census",
        "ddo_record_grade_cuts",
        "ddo_record_grade_require_producer",
        "ddo_record_grade_completion_scopes",
        "ddo_record_grade_dependency_scopes",
        "ddo_record_grade_require_frame",
        "ddo_require_record_grade_completion",
        "ddo_record_grade_dependencies_valid",
    }
