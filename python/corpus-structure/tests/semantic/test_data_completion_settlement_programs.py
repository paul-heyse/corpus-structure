"""PostgreSQL witness and settlement contracts generated from the captured model."""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_completion_settlement_native import (
    completion_settlement_native_sql,
)
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql, native_owner


def test_generated_settlement_programs_bind_in_actual_native_context(native_rollback):
    connection = native_rollback.connection
    execute_native_sql(connection, "CREATE EXTENSION IF NOT EXISTS plpgsql_check VERSION '2.10'")
    sql = completion_settlement_native_sql(get_metadata())
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, sql)
        for signature in (
            "data.ddo_witness_path(text)",
            "data.ddo_witness_records(jsonb,text)",
            "ops.ddo_assert_output_witnesses(ops.data_request,jsonb)",
            "ops.ddo_completion_seal(ops.data_request,jsonb,text,jsonb)",
            "ops.ddo_require_completion_correspondence(ops.data_request,jsonb,bigint,bigint,text)",
            "ops.ddo_require_episode_correspondence(ops.data_derivation,ops.data_completion_intent)",
            "ops.ddo_require_completion_live(ops.data_request,jsonb)",
            "ops.retain_data_completion_intent(jsonb)",
            "ops.adopt_data_completion_intent(jsonb)",
        ):
            if signature.startswith(("data.ddo_witness_path", "ops.ddo_completion_seal")):
                continue  # SQL-language routines bind at creation.
            errors = (
                connection.execute(
                    text(
                        "SELECT message FROM public.plpgsql_check_function_tb(CAST(:signature AS regprocedure),fatal_errors=>false) WHERE level='error'"
                    ),
                    {"signature": signature},
                )
                .scalars()
                .all()
            )
            assert errors == [], (signature, errors)
        assert connection.scalar(text("SELECT data.ddo_witness_path('/a~1b/~0c')")) == ["a/b", "~c"]
        assert connection.scalar(text("SELECT data.ddo_witness_path('')")) == []
        body = {"a/b": [{"~c": {"value": 1}}, {"~c": None}, {"~c": {"value": 2}}]}
        values = (
            connection.execute(
                text(
                    "SELECT * FROM data.ddo_witness_records(CAST(:body AS jsonb),'/a~1b/*/~0c/value')"
                ),
                {"body": json.dumps(body)},
            )
            .scalars()
            .all()
        )
        assert values == [1, 2]
        with pytest.raises(DBAPIError) as refusal, connection.begin_nested():
            connection.execute(text("SELECT * FROM data.ddo_witness_records('{}','/*')")).all()
        assert getattr(refusal.value.orig, "sqlstate", None) == "P0001"
