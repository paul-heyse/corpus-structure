"""Lower LinkML keyed inlined collections without introducing ordered-list meaning."""

from pathlib import Path

from alembic import op

revision = "semantic_0011"
down_revision = "semantic_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    previous = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_user").scalar_one()
    )
    conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
    conn.exec_driver_sql(
        Path(__file__).with_name("semantic_0011_inlined_maps.sql").read_text(),
        execution_options={"no_parameters": True},
    )
    conn.exec_driver_sql("SET LOCAL ROLE " + previous)


def downgrade() -> None:
    raise RuntimeError("keyed collection downgrade refused; rebuild a fresh database")
