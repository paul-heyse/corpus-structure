"""Bind final runtime implementation bytes without changing physical relations or kernels."""

from pathlib import Path

from alembic import op

revision = "semantic_0040"
down_revision = "semantic_0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    conn.exec_driver_sql(
        Path(__file__)
        .with_name("semantic_0040_admission.sql")
        .read_text()
        .replace("__MIGRATION_OWNER__", owner),
        execution_options={"no_parameters": True},
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + owner)


def downgrade() -> None:
    raise RuntimeError("implementation binding downgrade refused; rebuild an owned database")
