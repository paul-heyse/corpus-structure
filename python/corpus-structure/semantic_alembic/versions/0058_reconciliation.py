"""Qualified integrated PDF selection and common selected-content consumers."""
from pathlib import Path
from alembic import op
revision = "semantic_0058"
down_revision = "semantic_0057"
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    owner = conn.dialect.identifier_preparer.quote(conn.exec_driver_sql("SELECT current_user").scalar_one())
    for name in ("semantic_0058_reconciliation.sql", "semantic_0058_admission.sql"):
        conn.exec_driver_sql(Path(__file__).with_name(name).read_text().replace("__MIGRATION_OWNER__", owner), execution_options={"no_parameters": True})
    conn.exec_driver_sql("SET LOCAL ROLE " + owner)

def downgrade():
    raise RuntimeError("PDF reconciliation downgrade refused; rebuild an owned database")
