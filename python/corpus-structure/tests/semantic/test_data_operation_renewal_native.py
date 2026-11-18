"""Renewal programs bind the proposed tables while native control checks stay independent."""

import json

import yaml
from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy import text

from corpus_structure.semantic.data_operation_renewal import renewal_native_sql
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import (
    definition_from_sql,
    execute_native_sql,
    prepare_native_authoring,
)


def protocol():
    return metadata.info["physical_sources"]["data-operation-native.yaml"]


def test_renewal_program_uses_captured_contract_bounds():
    declaration = yaml.safe_load(protocol())
    declaration["definitions"]["renew_data_request_request"]["properties"]["lease_seconds"]["maximum"] = 75
    rendered = renewal_native_sql(metadata, yaml.safe_dump(declaration).encode())
    functions = parse_sql(rendered)
    assert len(functions) == 2
    assert all(isinstance(item.stmt, ast.CreateFunctionStmt) for item in functions)
    renewal = functions[1].stmt
    assert isinstance(renewal, ast.CreateFunctionStmt)
    body = next(option.arg[0].sval for option in renewal.options or () if option.defname == "as")
    assert "BETWEEN 1 AND 75" in body
    assert body.index("ops.ddo_lock_support") < body.index("FOR UPDATE INTO STRICT r") < body.index("FOR UPDATE INTO t")
    assert "source_digest" not in body


def test_renewal_programs_bind_against_real_tables_and_preserve_lost_envelope(commit_db_engine):
    with commit_db_engine.connect() as connection, connection.begin():
        statements = parse_sql(renewal_native_sql(metadata, protocol()))
        definitions = tuple(definition_from_sql(
            connection, RawStream()(item), source="generated-renewal", owner="corpus_sem_publisher",
        ) for item in statements)
        desired = prepare_native_authoring(
            connection, definitions, owned_authoring=True,
            check_plpgsql=frozenset(item.identity for item in definitions if item.identity.name == "renew_data_request"),
        )
        assert {item.identity.name for item in desired.desired} == {"ddo_lost_attempt", "renew_data_request"}
        # Exercise the SQL helper in a nested rollback scope, independent of a claim fixture.
        with connection.begin_nested() as temporary:
            for definition in definitions:
                execute_native_sql(connection, definition.sql)
            supplied = {"request_id": "request:actual", "generation": 3, "task_id": 9223372036854775807, "attempt": 7, "holder": "owner:actual"}
            actual = connection.execute(text("SELECT ops.ddo_lost_attempt(CAST(:payload AS jsonb),'revoked')"), {"payload": json.dumps(supplied)}).scalar_one()
            assert actual == {"payload": {**supplied, "state": "lost", "reason": "revoked"}}
            assert connection.execute(text("SELECT ops.ddo_lost_attempt(NULL,'revoked')")).scalar_one() is None
            temporary.rollback()
