"""Forward-only release/consumer contracts and governed analytical publication."""

from pathlib import Path

from alembic import op

revision = "semantic_0032"
down_revision = "semantic_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    for filename in (
        "semantic_0032_physical.sql",
        "semantic_0032_kernels.sql",
        "semantic_0032_admission.sql",
    ):
        conn.exec_driver_sql(
            Path(__file__).with_name(filename).read_text(),
            execution_options={"no_parameters": True},
        )
    conn.exec_driver_sql("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA sem TO " + owner)
    conn.exec_driver_sql("SET LOCAL ROLE " + owner)


def downgrade() -> None:
    raise RuntimeError("model closure downgrade refused; rebuild an owned database")
