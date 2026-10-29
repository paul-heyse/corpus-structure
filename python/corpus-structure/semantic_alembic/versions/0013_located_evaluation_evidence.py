"""Bind nested source citations and allow atomic source/inference stage lifetimes."""

from pathlib import Path

from alembic import op

revision = "semantic_0013"
down_revision = "semantic_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    previous = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
    conn.exec_driver_sql(
        Path(__file__).with_name("semantic_0013_evaluation_evidence.sql").read_text(),
        execution_options={"no_parameters": True},
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + previous)


def downgrade() -> None:
    raise RuntimeError(
        "destructive evaluation evidence downgrade refused; rebuild a fresh database"
    )
