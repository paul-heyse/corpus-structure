"""Link published entities to exact source declarations and retain the terminal context fence."""

from pathlib import Path

from alembic import op

revision = "semantic_0017"
down_revision = "semantic_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    previous = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    ddl, routines = (
        Path(__file__)
        .with_name("semantic_0017_entity_source.sql")
        .read_text()
        .split("-- Publisher-owned routines", 1)
    )
    conn.exec_driver_sql(ddl, execution_options={"no_parameters": True})
    conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
    conn.exec_driver_sql(routines, execution_options={"no_parameters": True})
    conn.exec_driver_sql(
        Path(__file__).with_name("semantic_0017_transport.sql").read_text(),
        execution_options={"no_parameters": True},
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + previous)


def downgrade() -> None:
    raise RuntimeError("destructive entity source downgrade refused; rebuild a fresh database")
