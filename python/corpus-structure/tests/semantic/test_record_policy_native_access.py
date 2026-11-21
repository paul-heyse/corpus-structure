"""Actual-login refusal and independent protected feature-frame partition controls."""

import json

import pytest
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.native_objects import execute_native_sql
from corpus_structure.semantic.native_program import Block, function, pg_type
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.record_policy_authority import GRADE_KIND
from corpus_structure.semantic.record_policy_native import (
    EVENT_FRAME_KIND,
    record_policy_native_sql,
)


def _install(connection, sql, names):
    prepared = prepare_sql(sql, source="policy-access-control")
    installed = set()
    for index, raw in enumerate(prepared.statements):
        if isinstance(raw.stmt, ast.CreateFunctionStmt) and raw.stmt.funcname:
            name = raw.stmt.funcname[-1].sval
            if name in names:
                execute_native_sql(connection, prepared.excerpt(index))
                installed.add(name)
    assert installed == set(names)


def test_feature_fit_requires_an_actual_restricted_login_not_role_swapping(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    _install(connection, record_policy_native_sql(), {"ddo_require_feature_fit_principal"})
    with (
        pytest.raises(DBAPIError, match="restricted actual fitting principal"),
        connection.begin_nested(),
    ):
        connection.execute(text("SELECT ops.ddo_require_feature_fit_principal()"))
    connection.exec_driver_sql("GRANT USAGE ON SCHEMA ops TO corpus_sem_fitter")
    connection.exec_driver_sql(
        "GRANT EXECUTE ON FUNCTION ops.ddo_require_feature_fit_principal() TO corpus_sem_fitter"
    )
    with connection.begin_nested():
        connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_fitter")
        with (
            pytest.raises(DBAPIError, match="restricted actual fitting principal"),
            connection.begin_nested(),
        ):
            connection.execute(text("SELECT ops.ddo_require_feature_fit_principal()"))
        connection.exec_driver_sql("RESET ROLE")


@pytest.fixture
def feature_body_control(infrastructure_rollback):
    from semantic.data_operation_binding_support import binding_source_recipe

    connection = infrastructure_rollback
    for schema in ("ops", "sem", "data"):
        connection.exec_driver_sql("CREATE SCHEMA " + schema)
    kinds = table("sem.data_kind_contract")
    connection.execute(CreateTable(kinds, include_foreign_key_constraints=[]))
    _install(connection, binding_source_recipe().codecs.decode(), {"ddo_json"})
    # The actual-login contract is tested separately above. This control
    # isolates the production decoded-kind/universe/partition disclosure rule.
    execute_native_sql(
        connection,
        function(
            "ops",
            "ddo_require_feature_fit_principal",
            parameters=(),
            returns=pg_type("void"),
            body=Block(()),
        ),
    )
    _install(connection, record_policy_native_sql(), {"ddo_feature_fit_body_access"})
    connection.execute(
        kinds.insert(),
        [
            dict(
                kind_contract=contract,
                kind=kind,
                body_schema={},
                meaning_schema={},
                member_schema={},
                member_contracts=[],
                universe=universe,
            )
            for contract, kind, universe in (
                ("grade", GRADE_KIND, "evaluator"),
                ("event", EVENT_FRAME_KIND, "evaluator"),
                ("ordinary", GRADE_KIND, "ordinary"),
            )
        ],
    )
    yield connection


def _body(version, partition, event):
    frame = ["mapping", [["partition", ["string", partition]]]]
    if event:
        frame = ["mapping", [["question", frame]]]
    return ["mapping", [["version", ["string", version]], ["frame", frame]]]


@pytest.mark.parametrize(
    ("contract", "version", "partition", "event", "expected"),
    [
        ("grade", "record-grade-1", "feature_fit", False, True),
        ("grade", "record-grade-1", "development", False, False),
        ("grade", "record-grade-1", "held_out", False, False),
        ("grade", "foreign-version", "feature_fit", False, False),
        ("ordinary", "record-grade-1", "feature_fit", False, False),
        ("event", "selected-operation-event-frame-product-1", "development", True, True),
        ("event", "selected-operation-event-frame-product-1", "feature_fit", True, True),
        ("event", "selected-operation-event-frame-product-1", "held_out", True, False),
        ("event", "record-grade-1", "feature_fit", True, False),
        ("absent", "record-grade-1", "feature_fit", False, False),
    ],
)
def test_feature_body_access_preserves_kind_universe_version_and_partition(
    feature_body_control, contract, version, partition, event, expected
):
    assert (
        feature_body_control.scalar(
            text("SELECT ops.ddo_feature_fit_body_access(:contract,CAST(:body AS jsonb))"),
            {"contract": contract, "body": json.dumps(_body(version, partition, event))},
        )
        is expected
    )
