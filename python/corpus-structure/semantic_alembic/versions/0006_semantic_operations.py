"""Fixed source and operation storage; semantic release never creates domain tables."""
from pathlib import Path
from alembic import op
revision = "semantic_0006"
down_revision = "semantic_0005"
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn = op.get_bind()
    database = conn.dialect.identifier_preparer.quote(conn.exec_driver_sql('SELECT current_database()').scalar_one())
    conn.exec_driver_sql(Path(__file__).with_name("semantic_0006_operations.sql").read_text(), execution_options={"no_parameters": True})
    conn.exec_driver_sql(Path(__file__).with_name("semantic_0006_publication.sql").read_text().replace('__semantic_database__',database), execution_options={"no_parameters": True})

def downgrade() -> None:
    raise RuntimeError("destructive operations downgrade refused; rebuild a fresh database")
