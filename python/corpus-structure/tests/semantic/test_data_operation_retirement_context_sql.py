"""Physical attempt and contextual product constraints use their declared owners."""

import json
from importlib.resources import files

import pytest
from sqlalchemy import MetaData, UniqueConstraint, insert, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_operation_identity import (
    body_identity,
    contextual_product_identity,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_protocol import render_data_task_guard
from corpus_structure.semantic.metadata import table


@pytest.mark.db
def test_retired_attempt_preserves_holder_until_a_new_claim_fence(semantic_bare_engine):
    source = files("corpus_structure.semantic").joinpath("sql/execution_guards.sql").read_text()
    protocol = files("corpus_structure.model").joinpath("semantic/data-operation-native.yaml").read_bytes()
    source = render_data_task_guard(protocol, source)
    association_start = source.index("   IF (NEW.data_request_id,")
    association_end = source.index(" END IF;", association_start) + len(" END IF;")
    fence_start = source.index("   IF NEW.attempt<>OLD.attempt THEN")
    fence_end = source.index("\n  END IF;\n  IF NEW.status='running'", fence_start)
    checks_start = source.index("  IF NEW.status='running' AND", fence_end)
    checks_end = source.index("  RETURN NEW;", checks_start)
    guard = (
        source[association_start:association_end]
        + source[fence_start:fence_end]
        + source[checks_start:checks_end]
    )
    with semantic_bare_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("""CREATE TEMP TABLE task_guard_case (
 id integer PRIMARY KEY, data_request_id text, data_generation integer, release_id text,
 invocation_key text, status text, attempt integer, claimed_by text,
 lease_until timestamptz, result_digest text)""")
            connection.exec_driver_sql("""INSERT INTO task_guard_case VALUES
 (1,'request:one',1,'release:one','invocation:one','running',1,'original-holder',
 clock_timestamp()+interval '1 hour',NULL)""")
            # Exercise the production state/fence branch, without replacing its
            # separate request admission or publication authority.
            connection.exec_driver_sql(
                "CREATE FUNCTION pg_temp.guard_task_case() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ BEGIN " + guard + " RETURN NEW; END $$"
            )
            connection.exec_driver_sql(
                "CREATE TRIGGER guard_task_case BEFORE UPDATE ON task_guard_case "
                "FOR EACH ROW EXECUTE FUNCTION pg_temp.guard_task_case()"
            )
            connection.exec_driver_sql(
                "UPDATE task_guard_case SET status='pending',lease_until=NULL"
            )
            assert tuple(
                connection.execute(
                    text("SELECT status,attempt,claimed_by,lease_until FROM task_guard_case")
                ).one()
            ) == ("pending", 1, "original-holder", None)
            for update, message in (
                ("claimed_by=NULL", "holder requires new attempt"),
                (
                    "status='running',lease_until=clock_timestamp()+interval '1 hour'",
                    "invalid data task transition",
                ),
                ("lease_until=clock_timestamp()+interval '1 hour'", "retains lease"),
            ):
                with connection.begin_nested() as savepoint:
                    with pytest.raises(DBAPIError, match=message):
                        connection.exec_driver_sql("UPDATE task_guard_case SET " + update)
                    savepoint.rollback()
            connection.exec_driver_sql(
                "UPDATE task_guard_case SET status='running',attempt=2,claimed_by='replacement',"
                "lease_until=clock_timestamp()+interval '1 hour'"
            )
            assert tuple(
                connection.execute(
                    text("SELECT status,attempt,claimed_by FROM task_guard_case")
                ).one()
            ) == ("running", 2, "replacement")
            with connection.begin_nested() as savepoint:
                with pytest.raises(DBAPIError, match="invalid data claim fence"):
                    connection.exec_driver_sql(
                        "UPDATE task_guard_case SET attempt=1,status='pending',lease_until=NULL"
                    )
                savepoint.rollback()
        finally:
            transaction.rollback()


@pytest.mark.db
def test_declared_product_primary_identity_allows_equal_body_in_distinct_scopes(
    semantic_bare_engine,
):
    product = table("kb.data_product").to_metadata(MetaData(), schema="pg_temp")
    assert not any(isinstance(constraint, UniqueConstraint) for constraint in product.constraints)
    body = body_identity(7)
    contexts = [
        SubjectContext("project", "local", "original", scope)
        for scope in (b'{"page":1}', b'{"page":2}')
    ]
    rows = [
        {
            "id": contextual_product_identity(
                kind="kind:integer", context=context, body=body.key
            ).key,
            "kind_contract": "kind:integer",
            "project_id": "project",
            "subject": "local",
            "original_source": "original",
            "analyzed_scope": context.record["analyzed_scope"],
            "canonical_body": ["integer", "7"],
            "body_digest": body.key,
        }
        for context in contexts
    ]
    assert rows[0]["id"] != rows[1]["id"]
    with semantic_bare_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(CreateTable(product, include_foreign_key_constraints=[]))
            connection.execute(insert(product), rows)
            assert set(connection.scalars(select(product.c.id))) == {row["id"] for row in rows}
            with connection.begin_nested() as savepoint:
                with pytest.raises(IntegrityError):
                    connection.execute(insert(product), rows[0])
                savepoint.rollback()
        finally:
            transaction.rollback()


@pytest.mark.db
def test_qualified_population_preserves_distinct_subject_definitions(semantic_bare_engine):
    source = files("corpus_structure.semantic").joinpath("sql/data_operation_bindings.sql").read_text()
    start = source.index("CREATE OR REPLACE FUNCTION ops.ddo_project_population(")
    end = source.index("-- Physical ledger slots", start)
    helpers = source[start:end].replace("ops.ddo_project_population", "pg_temp.ddo_project_population").replace("ops.ddo_binding_population_meaning", "pg_temp.ddo_binding_population_meaning")
    members = [
        {"member_id": name, "subject": "same-address", "subject_definition": name,
         "original_source": "same-document", "analyzed_scope": {"page": 3}}
        for name in ("document-subject", "view-subject")
    ]
    expected = [
        {"project_id": "project", **{key: value for key, value in member.items() if key != "member_id"}}
        for member in members
    ]
    with semantic_bare_engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql(helpers)
            witness = connection.execute(text("SELECT pg_temp.ddo_project_population('population:one',true,CAST(:members AS jsonb),'{}','project','qualified-context')"), {"members": json.dumps(members)}).scalar_one()
            assert witness["members"] == expected
            assert len({member["subject_definition"] for member in witness["members"]}) == 2
            meaning = connection.execute(text("SELECT pg_temp.ddo_binding_population_meaning(CAST(:witness AS jsonb),false)"), {"witness": json.dumps(witness)}).scalar_one()
            assert meaning == {"identity": "population:one", "complete": True,
                               "members": expected, "projection": "qualified-context"}
            del witness["members"][0]["subject_definition"]
            with connection.begin_nested() as savepoint:
                with pytest.raises(DBAPIError, match="invalid structured native population witness"):
                    connection.execute(text("SELECT pg_temp.ddo_binding_population_meaning(CAST(:witness AS jsonb),false)"), {"witness": json.dumps(witness)})
                savepoint.rollback()
        finally:
            transaction.rollback()
