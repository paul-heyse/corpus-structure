"""Forward deployment of finalized reference and selected-result enforcing functions."""
from pathlib import Path
from alembic import op
revision = 'semantic_0029'
down_revision = 'semantic_0028'
branch_labels = None
depends_on = None

def upgrade():
    conn=op.get_bind()
    owner=conn.dialect.identifier_preparer.quote(conn.exec_driver_sql('SELECT current_user').scalar_one())
    conn.exec_driver_sql(Path(__file__).with_name('semantic_0029_reference_boundaries.sql').read_text(),execution_options={'no_parameters':True})
    conn.exec_driver_sql('SET LOCAL ROLE '+owner)

def downgrade():
    raise RuntimeError('reference boundary downgrade refused; rebuild an owned database')
