"""Protected independent references and explicit selected completed results."""
from pathlib import Path
from alembic import op
revision = 'semantic_0028'
down_revision = 'semantic_0027'
branch_labels = None
depends_on = None

def upgrade():
    conn=op.get_bind()
    owner=conn.dialect.identifier_preparer.quote(conn.exec_driver_sql('SELECT current_user').scalar_one())
    conn.exec_driver_sql(Path(__file__).with_name('semantic_0028_reference.sql').read_text(),execution_options={'no_parameters':True})
    conn.exec_driver_sql('SET LOCAL ROLE '+owner)

def downgrade():
    raise RuntimeError('reference downgrade refused; rebuild an owned database')
