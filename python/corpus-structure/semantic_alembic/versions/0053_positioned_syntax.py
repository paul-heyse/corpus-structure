"""Retain typed positioned syntax from the released Lark frontend."""

from pathlib import Path

from alembic import op

revision = "semantic_0053"
down_revision = "semantic_0052"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    for name in ("semantic_0053_positioned_syntax.sql", "semantic_0053_admission.sql"):
        conn.exec_driver_sql(
            Path(__file__).with_name(name).read_text().replace("__MIGRATION_OWNER__", owner),
            execution_options={"no_parameters": True},
        )
    conn.exec_driver_sql("SET LOCAL ROLE " + owner)


def downgrade():
    raise RuntimeError("positioned syntax downgrade refused; rebuild an owned database")
