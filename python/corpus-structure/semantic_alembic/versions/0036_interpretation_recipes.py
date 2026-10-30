"""Admit explicit interpretation and science over fixed execution relations."""

from pathlib import Path

from alembic import op

revision = "semantic_0036"
down_revision = "semantic_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    # Relations and their existing contents are retained. The complete physical
    # authoring artifact is review input, not a second table-creation migration.
    # Kernels/reference guards are unchanged; replay would recreate their triggers.
    for filename in ("semantic_0036_admission.sql",):
        conn.exec_driver_sql(
            Path(__file__).with_name(filename).read_text().replace("__MIGRATION_OWNER__", owner),
            execution_options={"no_parameters": True},
        )
    conn.exec_driver_sql("SET LOCAL ROLE " + owner)


def downgrade() -> None:
    raise RuntimeError("analysis contract downgrade refused; rebuild an owned database")
