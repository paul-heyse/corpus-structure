"""Attempt retirement compiles exact diagnostic custody from captured declarations."""

import json

import pytest
import yaml
from pglast import ast, parse_sql
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_attempt_release_native import attempt_release_native_sql
from corpus_structure.semantic.data_operation_execution_evidence import execution_evidence_schema
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import (
    definition_from_sql,
    execute_native_sql,
    prepare_native_authoring,
)


def render(protocol=None):
    protocol = (
        metadata.info["physical_sources"]["data-operation-native.yaml"]
        if protocol is None
        else protocol
    )
    return attempt_release_native_sql(metadata, protocol, execution_evidence_schema())


def test_attempt_release_binds_diagnostic_limits_to_the_captured_wire():
    protocol = yaml.safe_load(metadata.info["physical_sources"]["data-operation-native.yaml"])
    protocol["definitions"]["d1_known_limitation"]["properties"]["request_json"]["maxLength"] = 777
    for alternative in protocol["definitions"]["d1_limitation_reply"]["oneOf"]:
        if alternative["properties"]["reason"].get("const") == "question_count":
            alternative["properties"]["limit"]["enum"] = [9]
        elif alternative["properties"]["reason"].get("const") == "packed_row_tokens":
            alternative["properties"]["row_tokens"]["maxItems"] = 7
    declaration = parse_sql(render(yaml.safe_dump(protocol).encode()))[0].stmt
    assert isinstance(declaration, ast.CreateFunctionStmt)
    body = next(
        option.arg[0].sval for option in declaration.options or () if option.defname == "as"
    )
    assert "> 777" in body and "<= 9" in body and "BETWEEN 1 AND 7" in body
    assert (
        body.index("ddo_lock_support")
        < body.index("FOR UPDATE INTO STRICT r")
        < body.index("FOR UPDATE INTO t")
    )


def test_attempt_release_has_bound_source_receipt_queries_and_refuses_unretired_failure(
    commit_db_engine,
):
    with commit_db_engine.connect() as connection, connection.begin():
        definition = definition_from_sql(
            connection, render(), source="generated-attempt-release", owner="corpus_sem_publisher"
        )
        assert prepare_native_authoring(
            connection,
            (definition,),
            owned_authoring=True,
            check_plpgsql=frozenset({definition.identity}),
        ).desired
        with connection.begin_nested() as replacement:
            execute_native_sql(connection, definition.sql)
            supplied = {
                "request_id": "request:absent",
                "generation": 1,
                "task_id": 1,
                "attempt": 1,
                "holder": "holder:actual",
                "physical_retirement": "uncertain",
                "failure": {"code": "compute-error", "message": "known failed computation"},
            }
            statement = text("SELECT ops.release_data_attempt(CAST(:payload AS jsonb))")
            with (
                pytest.raises(DBAPIError, match="exact known retirement/failure") as unretired,
                connection.begin_nested(),
            ):
                connection.execute(statement, {"payload": json.dumps(supplied)})
            assert getattr(unretired.value.orig, "sqlstate", None) == "P0001"
            with pytest.raises(DBAPIError) as absent, connection.begin_nested():
                connection.execute(
                    statement,
                    {"payload": json.dumps({**supplied, "physical_retirement": "confirmed"})},
                )
            assert getattr(absent.value.orig, "sqlstate", None) == "P0002"
            replacement.rollback()
