"""Exact-pin migration of existing addresses; no compatibility publication is invented."""

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations, ops
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.native_objects import NativeAuthoringError
from corpus_structure.semantic.published_address_migration import order_published_address_upgrade


def upgrade_operations():
    result = []
    for name in ("kb.source_view", "ops.native_region_artifact"):
        relation = table(name)
        result.append(
            ops.ModifyTableOps(
                relation.name,
                [
                    ops.AddColumnOp(
                        relation.name, relation.c[column]._copy(), schema=relation.schema
                    )
                    for column in ("native_build_id", "native_revision_id")
                ],
                schema=relation.schema,
            )
        )
    result.append(
        ops.ModifyTableOps(
            "pdf_published_revision",
            [
                ops.CreateUniqueConstraintOp(
                    "published_exact_pin",
                    "pdf_published_revision",
                    ["build_id", "task_id", "product_key", "logical_digest"],
                    schema="ops",
                )
            ],
            schema="ops",
        )
    )
    return ops.UpgradeOps(result)


def test_address_upgrade_refuses_unbound_before_ddl_then_backfills_exact_pin(semantic_bare_engine):
    with semantic_bare_engine.connect() as conn:
        tx = conn.begin()
        for schema in ("sem", "kb", "ops"):
            conn.exec_driver_sql("CREATE SCHEMA " + schema)
        for sql in (
            "CREATE TABLE ops.pdf_published_revision(build_id text,task_id bigint,"
            "product_key text,logical_digest text)",
            "CREATE TABLE kb.pdf_record_access(product_id text,revision_id text,pointer text)",
            "CREATE TABLE kb.pdf_record_region(product_id text,revision_id text,"
            "pointer text,region_index bigint)",
            "CREATE TABLE kb.source_view(id bigint,native_task_id bigint,native_product_key text,"
            "native_content_digest text,section_pointer text)",
            "CREATE TABLE ops.native_region_artifact(id text,native_task_id bigint,"
            "native_product_key text,native_content_digest text,pointer text,region_index bigint)",
            "CREATE FUNCTION sem.immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN "
            "RAISE EXCEPTION 'immutable'; END $$",
            "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE ON kb.source_view "
            "FOR EACH STATEMENT EXECUTE FUNCTION sem.immutable()",
            "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE "
            "ON ops.native_region_artifact "
            "FOR EACH STATEMENT EXECUTE FUNCTION sem.immutable()",
            "INSERT INTO ops.pdf_published_revision VALUES('exact',7,'integrated','digest'),"
            "('other',8,'integrated','other-digest')",
            "INSERT INTO kb.pdf_record_access VALUES('exact','exact','#/groups/1'),"
            "('other','other','#/groups/1')",
            "INSERT INTO kb.pdf_record_region VALUES('exact','exact','#/texts/1',0),"
            "('other','other','#/texts/1',0)",
            "INSERT INTO kb.source_view VALUES(1,7,'integrated','digest','#/groups/1'),"
            "(2,9,'native','unbound','#/groups/1')",
            "INSERT INTO ops.native_region_artifact "
            "VALUES('r',7,'integrated','digest','#/texts/1',0)",
        ):
            conn.exec_driver_sql(sql)
        upgrade = upgrade_operations()
        order_published_address_upgrade(upgrade)
        runner = Operations(MigrationContext.configure(conn))
        assert isinstance(upgrade.ops[0], ops.ExecuteSQLOp)
        with (
            pytest.raises(DBAPIError, match="unbound legacy published address"),
            conn.begin_nested(),
        ):
            runner.invoke(upgrade.ops[0])
        assert not conn.scalar(
            text("""SELECT EXISTS(SELECT FROM information_schema.columns
WHERE table_schema='kb' AND table_name='source_view' AND column_name='native_build_id')""")
        )
        # Correct the deliberately unbound test row; the migration itself never repairs it.
        conn.exec_driver_sql("ALTER TABLE kb.source_view DISABLE TRIGGER semantic_immutable")
        conn.exec_driver_sql("DELETE FROM kb.source_view WHERE id=2")
        conn.exec_driver_sql("ALTER TABLE kb.source_view ENABLE TRIGGER semantic_immutable")
        original_role = conn.scalar(text("SHOW role"))
        for operation in upgrade.ops:
            if isinstance(operation, ops.ModifyTableOps):
                for child in operation.ops:
                    runner.invoke(child)
            else:
                runner.invoke(operation)
        assert conn.scalar(text("SHOW role")) == original_role
        assert conn.exec_driver_sql(
            "SELECT native_build_id,native_revision_id FROM kb.source_view"
        ).all() == [("exact", "exact")]
        assert conn.exec_driver_sql(
            "SELECT native_build_id,native_revision_id FROM ops.native_region_artifact"
        ).all() == [("exact", "exact")]
        assert (
            conn.scalar(
                text("""SELECT count(*) FROM pg_trigger WHERE
 tgrelid IN ('kb.source_view'::regclass,'ops.native_region_artifact'::regclass)
 AND tgname='semantic_immutable' AND tgenabled='O'""")
            )
            == 2
        )
        assert (
            conn.scalar(
                text("""SELECT count(*) FROM information_schema.columns WHERE
 (table_schema,table_name) IN (('kb','source_view'),('ops','native_region_artifact'))
 AND column_name IN ('native_build_id','native_revision_id') AND is_nullable='NO'""")
            )
            == 4
        )
        with pytest.raises(DBAPIError, match="immutable"), conn.begin_nested():
            conn.exec_driver_sql("UPDATE kb.source_view SET native_build_id='other'")
        tx.rollback()


def test_address_ordering_is_unchanged_without_additions_and_refuses_partial_additions():
    unchanged = ops.UpgradeOps([ops.ExecuteSQLOp("SELECT 1")])
    original = tuple(unchanged.ops)
    order_published_address_upgrade(unchanged)
    assert tuple(unchanged.ops) == original
    partial = upgrade_operations()
    partial.ops.pop(0)
    with pytest.raises(NativeAuthoringError, match="all four"):
        order_published_address_upgrade(partial)
