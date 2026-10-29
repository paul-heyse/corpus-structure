"""Stable ordered source-input references for independent source reports."""
from pathlib import Path
from alembic import op
revision='semantic_0012'
down_revision='semantic_0011'
branch_labels=None
depends_on=None

def upgrade()->None:
    conn=op.get_bind()
    conn.exec_driver_sql(Path(__file__).with_name('semantic_0012_observation_inputs.sql').read_text(),execution_options={'no_parameters':True})

def downgrade()->None:
    raise RuntimeError('destructive source inputs downgrade refused; rebuild a fresh database')
