"""Real catalog index differences survive authoring; equal collated indexes are stable."""

from alembic.autogenerate import produce_migrations
from alembic.migration import MigrationContext
from alembic.operations.ops import CreateIndexOp, DropIndexOp, ModifyTableOps
from sqlalchemy import Column, Index, MetaData, Table, Text

from corpus_structure.semantic.alembic_indexes import plugin


def test_actual_catalog_collation_and_ordering_are_compared(semantic_database_at):
    with semantic_database_at("base") as engine, engine.begin() as conn:
        conn.exec_driver_sql("CREATE SCHEMA ac_index_reflection")
        conn.exec_driver_sql("CREATE TABLE ac_index_reflection.subjects(id text, body text)")
        conn.exec_driver_sql(
            "CREATE INDEX subject_order ON ac_index_reflection.subjects "
            '(id COLLATE "C" DESC NULLS LAST) INCLUDE(body)'
        )
        metadata = MetaData()
        relation = Table(
            "subjects",
            metadata,
            Column("id", Text),
            Column("body", Text),
            schema="ac_index_reflection",
        )
        Index(
            "subject_order",
            relation.c.id.collate("C").desc().nulls_last(),
            postgresql_include=["body"],
        )

        def changes():
            context = MigrationContext.configure(
                conn,
                opts=dict(
                    include_schemas=True,
                    include_name=lambda name, kind, parents: (
                        name == "ac_index_reflection" if kind == "schema" else True
                    ),
                    autogenerate_plugins=["alembic.autogenerate.*", plugin.name],
                ),
            )
            migration = produce_migrations(context, metadata)
            assert migration.upgrade_ops is not None
            return migration.upgrade_ops.ops

        assert changes() == []
        conn.exec_driver_sql("DROP INDEX ac_index_reflection.subject_order")
        conn.exec_driver_sql(
            "CREATE INDEX subject_order ON ac_index_reflection.subjects "
            '(id COLLATE "POSIX" DESC NULLS LAST) INCLUDE(body)'
        )
        changed = changes()
        assert len(changed) == 1
        assert isinstance(changed[0], ModifyTableOps)
        assert [type(operation) for operation in changed[0].ops] == [DropIndexOp, CreateIndexOp]
