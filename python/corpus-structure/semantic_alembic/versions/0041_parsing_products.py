"""Immutable original artifacts and relational parsing products with fenced publication."""

from pathlib import Path

from alembic import op

revision = "semantic_0041"
down_revision = "semantic_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    for suffix in ("parsing", "admission"):
        conn.exec_driver_sql(
            Path(__file__)
            .with_name(f"semantic_0041_{suffix}.sql")
            .read_text()
            .replace("__MIGRATION_OWNER__", owner),
            execution_options={"no_parameters": True},
        )
    conn.exec_driver_sql("SET LOCAL ROLE " + owner)


def downgrade() -> None:
    raise RuntimeError("parsing product downgrade refused; rebuild an owned database")
