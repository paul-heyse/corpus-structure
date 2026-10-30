"""Bind reference membership and grading to immutable completed source frames."""

from pathlib import Path

from alembic import op

revision = "semantic_0034"
down_revision = "semantic_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    for filename in ("semantic_0034_reference_source.sql", "semantic_0034_admission.sql"):
        conn.exec_driver_sql(
            Path(__file__).with_name(filename).read_text(),
            execution_options={"no_parameters": True},
        )
    conn.exec_driver_sql("SET LOCAL ROLE " + owner)


def downgrade() -> None:
    raise RuntimeError("reference source downgrade refused; rebuild an owned database")
