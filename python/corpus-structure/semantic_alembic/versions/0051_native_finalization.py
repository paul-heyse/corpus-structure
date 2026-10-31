"""Qualify located native evidence in the sealed occurrence finalization guard."""
from pathlib import Path
from alembic import op
revision='semantic_0051'
down_revision='semantic_0050'
branch_labels=None
depends_on=None

def upgrade():
    conn=op.get_bind()
    owner=conn.dialect.identifier_preparer.quote(conn.exec_driver_sql('SELECT current_user').scalar_one())
    for name in ('semantic_0051_native_finalization.sql','semantic_0051_admission.sql'):
        conn.exec_driver_sql(Path(__file__).with_name(name).read_text(),execution_options={'no_parameters':True})
    conn.exec_driver_sql('SET LOCAL ROLE '+owner)

def downgrade():
    raise RuntimeError('native evidence finalization downgrade refused; rebuild an owned database')
