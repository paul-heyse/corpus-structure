"""Enforce release-declared fact references at the protected value boundary."""

from pathlib import Path

from alembic import op

revision = "semantic_0019"
down_revision = "semantic_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    previous = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
    conn.exec_driver_sql(
        Path(__file__).with_name("semantic_0019_fact_references.sql").read_text(),
        execution_options={"no_parameters": True},
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + previous)


def downgrade() -> None:
    raise RuntimeError("destructive fact-reference downgrade refused; rebuild a fresh database")
