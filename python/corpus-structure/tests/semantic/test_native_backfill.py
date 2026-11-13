"""Real helper/function/view source normalization and transactional custody restoration."""

from dataclasses import replace

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import (
    NativeAuthoringError,
    admit_native,
    definition_from_sql,
    normalize_native_backfill,
    prepare_native_authoring,
)


def fixture(connection):
    connection.exec_driver_sql("CREATE SCHEMA sem")
    connection.exec_driver_sql('CREATE SCHEMA "native backfill"')
    owner = connection.scalar(text("SELECT current_user"))
    helper = definition_from_sql(
        connection,
        """
CREATE OR REPLACE FUNCTION "native backfill".helper(n integer) RETURNS integer
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$ SELECT n+1 $$
""",
        source="frozen helper",
        owner=owner,
        grants=(("corpus_sem_reader", "EXECUTE", False),),
    )
    consumer = definition_from_sql(
        connection,
        """
CREATE OR REPLACE FUNCTION "native backfill".consumer(n integer) RETURNS integer
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp
RETURN "native backfill".helper(n)
""",
        source="frozen bound consumer",
        owner=owner,
        grants=(("corpus_sem_reader", "EXECUTE", False),),
    )
    consumer = replace(
        consumer, role_bindings=(("$migration_owner", "sem_namespace_owner"),), bind_owner=True
    )
    view = definition_from_sql(
        connection,
        """
CREATE OR REPLACE VIEW "native backfill".answer AS
SELECT "native backfill".consumer(3) AS n
""",
        source="frozen view",
        owner=owner,
        grants=(("corpus_sem_reader", "SELECT", False),),
    )
    definitions = (helper, consumer, view)
    objects = prepare_native_authoring(connection, definitions, owned_authoring=True).desired
    operations = Operations(MigrationContext.configure(connection))
    for item in objects:
        NativeTransitionOp.native_transition(operations, NativeTransitionOp(None, item).payload())
    return definitions, objects


def oid_pins(connection):
    return connection.execute(
        text("""
SELECT '"native backfill".helper(integer)'::regprocedure::oid,
       '"native backfill".consumer(integer)'::regprocedure::oid,
       '"native backfill".answer'::regclass::oid
""")
    ).one()


def test_backfill_normalization_preserves_exact_frozen_dependents_and_oids(semantic_bare_engine):
    with semantic_bare_engine.connect() as connection, connection.begin():
        definitions, objects = fixture(connection)
        before = oid_pins(connection)
        # The old helper was previously outside managed state; its already managed
        # SQL-standard function and view are the explicit frozen normalization context.
        normalized = normalize_native_backfill(
            connection, definitions[:1], context=objects[1:], owned_authoring=True
        )
        assert len(normalized) == 1
        assert normalized[0].catalog == objects[0].catalog
        assert oid_pins(connection) == before
        admit_native(connection, objects)
        assert connection.scalar(text('SELECT n FROM "native backfill".answer')) == 4
        # Existing declaration order may put a newly managed helper after a view.
        # Observed bounded dependencies, rather than tuple position, govern drops.
        current = prepare_native_authoring(
            connection,
            definitions,
            predecessor=(objects[2], objects[0], objects[1]),
            owned_authoring=True,
        )
        assert tuple(item.identity for item in current.desired) == tuple(
            item.identity for item in objects
        )
        assert oid_pins(connection) == before
        admit_native(connection, objects)


def test_backfill_refuses_external_dependents_and_restores_owned_context(semantic_bare_engine):
    with semantic_bare_engine.connect() as connection, connection.begin():
        definitions, objects = fixture(connection)
        connection.exec_driver_sql("""CREATE VIEW "native backfill".external AS
SELECT "native backfill".consumer(7) AS n""")
        before = oid_pins(connection)
        with pytest.raises(NativeAuthoringError, match="dependent"):
            normalize_native_backfill(
                connection, definitions[:1], context=objects[1:], owned_authoring=True
            )
        assert oid_pins(connection) == before
        admit_native(connection, objects)
        assert connection.scalar(text('SELECT n FROM "native backfill".external')) == 8
