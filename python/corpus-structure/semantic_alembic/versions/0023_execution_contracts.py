"""Frozen finite lifecycle and native conditional enforcement kernels."""

from pathlib import Path

from alembic import op

revision = "semantic_0023"
down_revision = "semantic_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    previous = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    conn.exec_driver_sql(
        Path(__file__)
        .with_name("semantic_0023_execution.sql")
        .read_text()
        .replace("__MIGRATION_OWNER__", previous),
        execution_options={"no_parameters": True},
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + previous)


def downgrade() -> None:
    raise RuntimeError("execution-contract downgrade refused; rebuild an owned database")
