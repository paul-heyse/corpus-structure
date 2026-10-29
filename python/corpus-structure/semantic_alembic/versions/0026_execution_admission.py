"""Enable composed bindings only against the exact enforcing native deployment."""

from pathlib import Path

from alembic import op

revision = "semantic_0026"
down_revision = "semantic_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    conn.exec_driver_sql(
        Path(__file__)
        .with_name("semantic_0026_admission.sql")
        .read_text()
        .replace("__MIGRATION_OWNER__", owner),
        execution_options={"no_parameters": True},
    )


def downgrade() -> None:
    raise RuntimeError("execution admission downgrade refused; rebuild an owned database")
