"""Model-built single claims keep native locks, public shapes and local failure states."""

import json

import pytest
import yaml
from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_claim_native import claim_native_sql
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import (
    definition_from_sql,
    execute_native_sql,
    prepare_native_authoring,
)


def render(protocol=None):
    return claim_native_sql(
        get_metadata(),
        get_metadata().info["physical_sources"]["data-operation-native.yaml"]
        if protocol is None
        else protocol,
    )


def test_claims_use_the_captured_wire_lease_contract_and_original_lock_order():
    protocol = yaml.safe_load(get_metadata().info["physical_sources"]["data-operation-native.yaml"])
    protocol["definitions"]["claim_data_request_request"]["properties"]["lease_seconds"][
        "maximum"
    ] = 61
    statements = parse_sql(render(yaml.safe_dump(protocol).encode()))
    assert len(statements) == 2
    claim = statements[1].stmt
    assert isinstance(claim, ast.CreateFunctionStmt)
    body = next(option.arg[0].sval for option in claim.options or () if option.defname == "as")
    assert "BETWEEN 1 AND 61" in body
    assert (
        body.index("ddo_lock_support")
        < body.index("FOR UPDATE INTO STRICT r")
        < body.index("FOR UPDATE INTO STRICT t")
    )
    assert body.index("INTO STRICT binding_use") < body.index("UPDATE ops.task")


def test_claim_queries_bind_on_postgresql_and_invalid_leases_refuse_before_lookup(commit_db_engine):
    with commit_db_engine.connect() as connection, connection.begin():
        definitions = tuple(
            definition_from_sql(
                connection,
                RawStream()(item),
                source="generated-claim",
                owner="corpus_sem_publisher",
            )
            for item in parse_sql(render())
        )
        assert (
            len(
                prepare_native_authoring(
                    connection,
                    definitions,
                    owned_authoring=True,
                    check_plpgsql=frozenset(item.identity for item in definitions),
                ).desired
            )
            == 2
        )
        with connection.begin_nested() as replacement:
            for definition in definitions:
                execute_native_sql(connection, definition.sql)
            payload = {
                "request_id": "request:absent",
                "generation": 1,
                "holder": "holder:actual",
                "lease_seconds": 0,
            }
            statement = text("SELECT ops.ddo_claim_data_request(CAST(:payload AS jsonb))")
            with (
                pytest.raises(DBAPIError, match="invalid holder/lease") as invalid,
                connection.begin_nested(),
            ):
                connection.execute(statement, {"payload": json.dumps(payload)})
            assert getattr(invalid.value.orig, "sqlstate", None) == "23514"
            with pytest.raises(DBAPIError) as absent, connection.begin_nested():
                connection.execute(
                    statement, {"payload": json.dumps({**payload, "lease_seconds": 30})}
                )
            assert getattr(absent.value.orig, "sqlstate", None) == "P0002"
            replacement.rollback()
