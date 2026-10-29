"""Deploy reviewed analytical source fence and writer read privileges.

Frozen companion SQL intentionally imports no evolving application code.
"""

from pathlib import Path

from alembic import op

revision = "semantic_0004"
down_revision = "semantic_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        Path(__file__).with_name("semantic_0004_arrow_analysis.sql").read_text(),
        execution_options={"no_parameters": True},
    )


def downgrade() -> None:
    raise RuntimeError(
        "destructive semantic publication downgrade refused; rebuild a fresh database"
    )
