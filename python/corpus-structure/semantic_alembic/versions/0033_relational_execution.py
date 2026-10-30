"""Forward-only release-scoped execution projections and bounded native effects."""

from pathlib import Path

from alembic import op

revision = "semantic_0033"
down_revision = "semantic_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    for filename in (
        "semantic_0033_physical.sql",
        "semantic_0033_kernels.sql",
        "semantic_0033_admission.sql",
    ):
        conn.exec_driver_sql(
            Path(__file__).with_name(filename).read_text().replace("__MIGRATION_OWNER__", owner),
            execution_options={"no_parameters": True},
        )
    conn.exec_driver_sql("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA sem TO " + owner)
    conn.exec_driver_sql(
        "GRANT EXECUTE ON FUNCTION ops.lock_execution_run(bigint,text),ops.require_transition(text,text,text,text),ops.execution_edge(text,text,text,text) TO "
        + owner
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + owner)


def downgrade() -> None:
    raise RuntimeError("model closure downgrade refused; rebuild an owned database")
