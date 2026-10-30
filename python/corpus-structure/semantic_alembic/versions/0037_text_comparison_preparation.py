"""Persist source-build token layouts and admit model-bound comparison preparation."""

from pathlib import Path

from alembic import op
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

revision = "semantic_0037"
down_revision = "semantic_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    op.add_column("rendition_build", Column("text_layout", JSONB(), nullable=True), schema="ops")
    conn.exec_driver_sql(
        Path(__file__)
        .with_name("semantic_0037_text_layout.sql")
        .read_text()
        .replace("__MIGRATION_OWNER__", owner)
    )
    conn.exec_driver_sql(
        Path(__file__)
        .with_name("semantic_0037_admission.sql")
        .read_text()
        .replace("__MIGRATION_OWNER__", owner),
        execution_options={"no_parameters": True},
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + owner)


def downgrade() -> None:
    raise RuntimeError("source-build artifact downgrade refused; rebuild an owned database")
