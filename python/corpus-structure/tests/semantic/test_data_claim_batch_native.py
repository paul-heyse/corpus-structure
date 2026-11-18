"""Set claims preserve item positions, duplicate refusals and exception boundaries."""

import json

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, Text, func, insert, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_claim_batch_native import claim_batch_native_sql
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import (
    definition_from_sql,
    execute_native_sql,
    prepare_native_authoring,
)
from corpus_structure.semantic.native_program import (
    Block,
    CatchCheckViolation,
    Raise,
    Return,
    Sql,
    core_variable,
    function,
    pg_type,
)


def test_set_claim_preserves_order_and_duplicate_refusal_without_external_work(commit_db_engine):
    with commit_db_engine.connect() as connection, connection.begin():
        definition = definition_from_sql(
            connection,
            claim_batch_native_sql(metadata),
            source="generated-set-claim",
            owner="corpus_sem_publisher",
        )
        assert prepare_native_authoring(
            connection,
            (definition,),
            owned_authoring=True,
            check_plpgsql=frozenset({definition.identity}),
        ).desired
        with connection.begin_nested() as replacement:
            execute_native_sql(connection, definition.sql)
            first = {"request_id": "request:absent-a", "generation": 1}
            second = {"request_id": "request:absent-b", "generation": 1}
            payload = {
                "items": [first, second, first],
                "holder": "holder:actual",
                "lease_seconds": 30,
            }
            statement = text("SELECT ops.claim_data_requests(CAST(:payload AS jsonb))")
            actual = connection.execute(statement, {"payload": json.dumps(payload)}).scalar_one()
            refusal = {
                "state": "refused",
                "sqlstate": "23514",
                "reason": "claim item request is absent",
            }
            assert actual == {"payload": {"items": [refusal, refusal, refusal]}}
            assert connection.execute(
                statement, {"payload": json.dumps({**payload, "items": []})}
            ).scalar_one() == {"payload": {"items": []}}
            replacement.rollback()


@pytest.mark.parametrize("state", ("23514", "42501"))
def test_item_subtransaction_rolls_back_and_only_check_violation_is_caught(
    semantic_bare_engine, state
):
    with semantic_bare_engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA item_control")
        effects = Table("effects", MetaData(), Column("value", Integer), schema="item_control")
        effects.create(connection)
        source = function(
            "item_control",
            "refusal",
            parameters=(),
            returns=pg_type("jsonb"),
            body=Block(
                (
                    CatchCheckViolation(
                        (
                            Sql(insert(effects).values(value=1)),
                            Raise("controlled item refusal", state),
                        ),
                        (
                            Return(
                                func.jsonb_build_object(
                                    "state",
                                    core_variable("sqlstate", Text()),
                                    "message",
                                    core_variable("sqlerrm", Text()),
                                )
                            ),
                        ),
                    ),
                    Return(func.jsonb_build_object("unexpected", True)),
                )
            ),
            search_path=("pg_catalog", "pg_temp"),
        )
        execute_native_sql(connection, source)
        if state == "23514":
            assert connection.execute(text("SELECT item_control.refusal()")).scalar_one() == {
                "state": "23514",
                "message": "controlled item refusal",
            }
        else:
            with pytest.raises(DBAPIError) as permission, connection.begin_nested():
                connection.execute(text("SELECT item_control.refusal()"))
            assert getattr(permission.value.orig, "sqlstate", None) == "42501"
        assert connection.execute(select(func.count()).select_from(effects)).scalar_one() == 0
