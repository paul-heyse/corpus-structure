from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from alembic.autogenerate import produce_migrations, render_python_code
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, Integer, MetaData, Table, text

from corpus_structure.semantic.alembic_native import NativeTransitionOp, plugin
from corpus_structure.semantic.native_objects import (
    NativeAuthoring,
    admit_native,
    definition_from_sql,
    execute_native_sql,
    observe_native,
    prepare_native_authoring,
)


def upgrades(script):
    result = script.upgrade_ops
    assert result is not None
    return result


def definitions(conn, *, label="old:100%", strict="", threshold=0):
    owner = conn.scalar(text("SELECT current_user"))
    return tuple(
        definition_from_sql(
            conn,
            sql,
            source=source,
            owner=owner,
            grants=(("corpus_sem_reader", "EXECUTE", False),) if kind == "function" else (),
        )
        for sql, source, kind in [
            (
                f"""CREATE OR REPLACE FUNCTION "native test"."F :%"(INOUT n integer, OUT label text)
 RETURNS record LANGUAGE sql STABLE {strict} SET search_path=pg_catalog,pg_temp
 AS $body$ SELECT n, '{label}'::text $body$""",
                "reader.sql",
                "function",
            ),
            (
                """CREATE OR REPLACE FUNCTION "native test".guard() RETURNS trigger
 LANGUAGE plpgsql AS $$ BEGIN RETURN NEW; END $$""",
                "guard.sql",
                "function",
            ),
            (
                'CREATE OR REPLACE VIEW "native test".v AS SELECT * FROM "native test"."F :%"(3)',
                "view.sql",
                "view",
            ),
            (
                f"""CREATE TRIGGER guarded BEFORE INSERT ON "native test".items
 FOR EACH ROW WHEN (NEW.n>{threshold}) EXECUTE FUNCTION "native test".guard()""",
                "trigger.sql",
                "trigger",
            ),
        ]
    )


def install(conn, objects):
    for obj in objects:
        for sql in obj.statements:
            execute_native_sql(conn, sql)


def context(conn):
    return MigrationContext.configure(
        conn,
        opts={
            "include_schemas": True,
            "include_name": lambda name, typ, parents: (
                name == "native test" if typ == "schema" else True
            ),
            "autogenerate_plugins": ["alembic.autogenerate.*", plugin.name],
        },
    )


def test_native_plugin_frozen_payload_actual_properties_and_caller_rollback(
    semantic_bare_engine, tmp_path
):
    md = MetaData()
    Table("items", md, Column("n", Integer), schema="native test")
    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql('CREATE SCHEMA "native test"')
        md.create_all(conn)
        execute_native_sql(
            conn,
            'CREATE FUNCTION "native test"."F :%"(text) RETURNS text LANGUAGE sql '
            "AS $$ SELECT $1 $$",
        )
        previous = definitions(conn)
        initial = prepare_native_authoring(conn, previous, owned_authoring=True)
        install(conn, initial.desired)
        conn.exec_driver_sql('GRANT USAGE ON SCHEMA "native test" TO corpus_sem_reader')
    with semantic_bare_engine.connect() as conn:
        transaction = conn.begin()
        authoring = prepare_native_authoring(
            conn,
            definitions(conn, label="new:100%", strict="STRICT", threshold=1),
            predecessor=definitions(conn),
            owned_authoring=True,
        )
        migration = context(conn)
        migration.opts["native_authoring"] = authoring
        # Ordinary Alembic changes coexist with native directives.
        md.tables["native test.items"].append_column(Column("extra", Integer))
        script = produce_migrations(migration, md)
        native = [item for item in upgrades(script).ops if isinstance(item, NativeTransitionOp)]
        assert {op.identity.kind for op in native} == {"function", "trigger"}
        assert any(not isinstance(item, NativeTransitionOp) for item in upgrades(script).ops)
        code = render_python_code(upgrades(script), migration_context=migration)
        assert "op.native_transition(" in code
        assert "new:100%" in code
        operations = Operations(migration)
        for op in native:
            operations.invoke(op)
        admit_native(conn, authoring.desired)
        assert conn.exec_driver_sql('SELECT label FROM "native test".v').scalar_one() == "new:100%"
        assert (
            conn.exec_driver_sql('SELECT "native test"."F :%%"(\'unowned\'::text)').scalar_one()
            == "unowned"
        )
        assert conn.scalar(
            text(
                "SELECT "
                "has_function_privilege('corpus_sem_reader',to_regprocedure(:signature)"
                ",'EXECUTE')"
            ),
            {"signature": native[0].identity.qualified},
        )
        assert (
            upgrades(produce_migrations(migration, md)).ops[0].__class__.__name__
            != "NativeTransitionOp"
        )
        conn.exec_driver_sql('ALTER FUNCTION "native test"."F :%%"(integer) SET search_path=public')
        with pytest.raises(ValueError, match=r"admission failed.*config"):
            admit_native(conn, authoring.desired)
        transaction.rollback()
    with semantic_bare_engine.connect() as conn:
        assert conn.exec_driver_sql('SELECT label FROM "native test".v').scalar_one() == "old:100%"
        payload = native[0].payload()
        # A fresh process invokes the frozen literal without importing current author generators.
        program = """import json,sys
from sqlalchemy import create_engine
from alembic.migration import MigrationContext
from alembic.operations import Operations
from corpus_structure.semantic import alembic_native
assert "corpus_structure.semantic.native_products" not in sys.modules
engine=create_engine(sys.argv[1])
with engine.connect() as conn:
 with conn.begin():
  Operations(MigrationContext.configure(conn)).native_transition(json.loads(sys.argv[2]))
  assert conn.exec_driver_sql('SELECT label FROM "native test".v').scalar_one()=="new:100%"
  conn.rollback()
engine.dispose()
"""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                program,
                semantic_bare_engine.url.render_as_string(hide_password=False),
                json.dumps(payload),
            ],
            capture_output=True,
            text=True,
            env=os.environ,
        )
        assert result.returncode == 0, result.stderr
        conn.rollback()
        for operation in native:
            Operations(MigrationContext.configure(conn)).invoke(operation)
        conn.commit()
    from sqlalchemy import create_engine

    reader = create_engine(semantic_bare_engine.url.set(username="corpus_sem_reader"))
    try:
        with reader.connect() as conn:
            assert (
                conn.exec_driver_sql('SELECT label FROM "native test"."F :%%"(8)').scalar_one()
                == "new:100%"
            )
    finally:
        reader.dispose()


def test_explicit_scope_retirement_reverse_and_missing_context(semantic_bare_engine):
    md = MetaData()
    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql('CREATE SCHEMA "native test"')
        owner = conn.scalar(text("SELECT current_user"))
        definition = definition_from_sql(
            conn,
            'CREATE OR REPLACE FUNCTION "native test".f() RETURNS integer LANGUAGE '
            "sql AS $$SELECT 1$$",
            source="one.sql",
            owner=owner,
        )
        before = prepare_native_authoring(conn, (definition,), owned_authoring=True).desired
        install(conn, before)
        migration = context(conn)
        with pytest.raises(ValueError, match="explicit native_authoring"):
            produce_migrations(migration, md)
        with pytest.raises(ValueError, match="retirement"):
            NativeAuthoring((), before)
        migration.opts["native_authoring"] = NativeAuthoring(
            (), before, frozenset({definition.identity})
        )
        script = produce_migrations(migration, md)
        op = upgrades(script).ops[0]
        operations = Operations(migration)
        operations.invoke(op)
        assert observe_native(conn, definition.identity) is None
        operations.invoke(op.reverse())
        assert conn.exec_driver_sql('SELECT "native test".f()').scalar_one() == 1
        conn.exec_driver_sql(
            'CREATE OR REPLACE FUNCTION "native test".f() RETURNS integer LANGUAG'
            "E sql AS $$SELECT 2$$"
        )
        with pytest.raises(ValueError, match="stale native before-state"):
            operations.invoke(op)


def test_identity_callable_default_upstream_defect_and_retained_adapter(semantic_bare_engine):
    from sqlalchemy import Identity

    from corpus_structure.semantic.alembic_defaults import plugin as defaults_plugin

    md = MetaData()
    Table(
        "identified",
        md,
        Column("id", Integer, Identity(), primary_key=True),
        schema="identity_test",
    )
    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA identity_test")
        md.create_all(conn)
        opts = {
            "include_schemas": True,
            "include_name": lambda name, typ, parents: (
                name == "identity_test" if typ == "schema" else True
            ),
            "compare_server_default": lambda *args: None,
            "autogenerate_plugins": ["alembic.autogenerate.*"],
        }
        # Exact pinned 1.20.1 defect, upstream comparison without our adapter.
        with pytest.raises(AttributeError, match=r"Identity.*arg"):
            produce_migrations(MigrationContext.configure(conn, opts=opts), md)
        opts["autogenerate_plugins"].append(defaults_plugin.name)
        assert upgrades(
            produce_migrations(MigrationContext.configure(conn, opts=opts), md)
        ).is_empty()


def test_result_recreation_orders_explicit_dependents_and_preserves_reverse(semantic_bare_engine):
    from sqlalchemy.exc import DBAPIError

    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql('CREATE SCHEMA "native test"')
        owner = conn.scalar(text("SELECT current_user"))

        def pair(kind, value):
            return tuple(
                definition_from_sql(conn, sql, source="result.sql", owner=owner)
                for sql in (
                    f'CREATE OR REPLACE FUNCTION "native test".f() RETURNS {kind} '
                    f"LANGUAGE sql AS $$SELECT {value}$$",
                    'CREATE OR REPLACE VIEW "native test".v AS SELECT "native test".f() AS value',
                )
            )

        before = pair("integer", "1")
        install(conn, prepare_native_authoring(conn, before, owned_authoring=True).desired)
        after = pair("text", "'two'::text")
        authoring = prepare_native_authoring(conn, after, predecessor=before, owned_authoring=True)
        migration = context(conn)
        migration.opts["native_authoring"] = authoring
        with pytest.raises(ValueError, match="result change requires explicit recreation"):
            produce_migrations(migration, MetaData())
        migration.opts["native_authoring"] = NativeAuthoring(
            authoring.desired,
            authoring.predecessor,
            recreate=frozenset(item.identity for item in before),
        )
        script = produce_migrations(migration, MetaData())
        assert [(op.identity.kind, op.after is not None) for op in upgrades(script).ops] == [
            ("view", False),
            ("function", False),
            ("function", True),
            ("view", True),
        ]
        for op in upgrades(script).ops:
            Operations(migration).invoke(op)
        assert conn.exec_driver_sql('SELECT value FROM "native test".v').scalar_one() == "two"
        assert upgrades(produce_migrations(migration, MetaData())).is_empty()
        for op in reversed(upgrades(script).ops):
            Operations(migration).invoke(op.reverse())
        assert conn.exec_driver_sql('SELECT value FROM "native test".v').scalar_one() == 1
        # Unknown dependents are neither adopted nor removed by normalization.
        conn.exec_driver_sql('CREATE VIEW "native test".unowned AS SELECT "native test".f()')
        with pytest.raises(DBAPIError, match=r"dependent objects|depend on it"):
            prepare_native_authoring(
                conn, (after[0],), predecessor=(before[0],), owned_authoring=True
            )
        assert conn.exec_driver_sql('SELECT * FROM "native test".unowned').scalar_one() == 1


def test_frozen_revision_history_and_object_rollback_share_caller_connection(
    semantic_bare_engine, tmp_path
):
    from alembic import command
    from alembic.config import Config

    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql('CREATE SCHEMA "native test"')
        owner = conn.scalar(text("SELECT current_user"))
        before = definition_from_sql(
            conn,
            'CREATE OR REPLACE FUNCTION "native test".f() RETURNS integer LANGUAGE '
            "sql AS $$SELECT 1$$",
            source="before.sql",
            owner=owner,
        )
        after = definition_from_sql(
            conn,
            'CREATE OR REPLACE FUNCTION "native test".f() RETURNS integer LANGUAGE '
            "sql AS $$SELECT 2$$",
            source="after.sql",
            owner=owner,
        )
        authoring = prepare_native_authoring(
            conn, (after,), predecessor=(before,), owned_authoring=True
        )
        install(conn, authoring.predecessor)
        operation = NativeTransitionOp(authoring.predecessor[0], authoring.desired[0])
    (tmp_path / "versions").mkdir()
    (tmp_path / "env.py").write_text("""from alembic import context
connection=context.config.attributes['connection']
context.configure(connection=connection)
with context.begin_transaction():
 context.run_migrations()
""")
    (tmp_path / "versions/native_test.py").write_text(f"""from alembic import op
from corpus_structure.semantic import alembic_native
revision='native_test'
down_revision=None
def upgrade():
 op.native_transition({operation.payload()!r})
def downgrade():
 op.native_transition({operation.reverse().payload()!r})
""")
    cfg = Config()
    cfg.set_main_option("script_location", str(tmp_path))
    with semantic_bare_engine.connect() as conn:
        tx = conn.begin()
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
        assert MigrationContext.configure(conn).get_current_revision() == "native_test"
        assert conn.exec_driver_sql('SELECT "native test".f()').scalar_one() == 2
        tx.rollback()
        assert MigrationContext.configure(conn).get_current_revision() is None
        assert conn.exec_driver_sql('SELECT "native test".f()').scalar_one() == 1


def test_desired_acl_does_not_adopt_ambient_default_grants(semantic_bare_engine):
    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql('CREATE SCHEMA "native test"')
        conn.exec_driver_sql(
            'ALTER DEFAULT PRIVILEGES IN SCHEMA "native test" GRANT EXECUTE ON FU'
            "NCTIONS TO corpus_sem_reader"
        )
        owner = conn.scalar(text("SELECT current_user"))
        definition = definition_from_sql(
            conn,
            'CREATE OR REPLACE FUNCTION "native test".f() RETURNS integer LANGUAGE '
            "sql AS $$SELECT 1$$",
            source="private.sql",
            owner=owner,
        )
        desired = prepare_native_authoring(conn, (definition,), owned_authoring=True).desired[0]
        assert desired.catalog["acl"] == [[owner, "EXECUTE", False]]
        role = conn.scalar(text("SELECT current_setting('role')"))
        Operations(MigrationContext.configure(conn)).invoke(NativeTransitionOp(None, desired))
        assert conn.scalar(text("SELECT current_setting('role')")) == role
        assert not conn.scalar(
            text(
                "SELECT has_function_privilege('corpus_sem_reader','\"native test\".f()','EXECUTE')"
            )
        )


def test_out_result_slots_are_compared_beyond_record_return_type(semantic_bare_engine):
    with semantic_bare_engine.begin() as conn:
        conn.exec_driver_sql('CREATE SCHEMA "native test"')
        owner = conn.scalar(text("SELECT current_user"))

        def declared(kind):
            return definition_from_sql(
                conn,
                f"""CREATE OR REPLACE FUNCTION "native test".out_slots(
 IN p integer,OUT n integer,OUT label {kind})
 RETURNS record LANGUAGE plpgsql AS $$BEGIN n:=p; label:='123'; END$$""",
                source="out-slots.sql",
                owner=owner,
            )

        previous, desired = declared("text"), declared("integer")
        authoring = prepare_native_authoring(
            conn, (desired,), predecessor=(previous,), owned_authoring=True
        )
        before, after = authoring.predecessor[0], authoring.desired[0]
        assert before.identity == after.identity
        assert before.catalog["result"] == after.catalog["result"] == "record"
        assert before.catalog["body"] == after.catalog["body"]
        assert before.catalog["arguments"] == "p integer, OUT n integer, OUT label text"
        assert after.catalog["arguments"] == "p integer, OUT n integer, OUT label integer"
        with pytest.raises(ValueError, match="argument change requires explicit recreation"):
            NativeTransitionOp(before, after)
