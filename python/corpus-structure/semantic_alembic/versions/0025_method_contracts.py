"""Freeze method applicability in the native task constructor."""
from pathlib import Path
from alembic import op

revision = "semantic_0025"
down_revision = "semantic_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        Path(__file__).with_name("semantic_0025_methods.sql").read_text(),
        execution_options={"no_parameters": True},
    )


def downgrade() -> None:
    raise RuntimeError("method contract downgrade refused; rebuild an owned database")
