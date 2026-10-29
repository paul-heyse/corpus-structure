"""Honor admitted SourceStatement descendants at the native occurrence boundary."""
from pathlib import Path
from alembic import op

revision = 'semantic_0031'
down_revision = 'semantic_0030'
branch_labels = None
depends_on = None

def upgrade() -> None:
    conn=op.get_bind()
    owner=conn.dialect.identifier_preparer.quote(conn.exec_driver_sql('SELECT current_user').scalar_one())
    conn.exec_driver_sql(Path(__file__).with_name('semantic_0031_statement_inheritance.sql').read_text(),execution_options={'no_parameters':True})
    conn.exec_driver_sql('SET LOCAL ROLE '+owner)

def downgrade() -> None:
    raise RuntimeError('statement inheritance downgrade refused; rebuild an owned database')
