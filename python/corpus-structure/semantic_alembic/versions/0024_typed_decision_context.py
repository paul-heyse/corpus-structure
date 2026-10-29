"""Typed decision context and lossless source-coverage translation."""

from pathlib import Path

from alembic import op

revision = "semantic_0024"
down_revision = "semantic_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql(
        Path(__file__).with_name("semantic_0024_decisions.sql").read_text(),
        execution_options={"no_parameters": True},
    )
    previous = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
    conn.exec_driver_sql(
        Path(__file__).with_name("semantic_0024_transport.sql").read_text(),
        execution_options={"no_parameters": True},
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + previous)


def downgrade() -> None:
    raise RuntimeError("typed decision downgrade refused; rebuild an owned database")
