"""Hold the exact input realization stable for each short packet preparation transaction."""
from pathlib import Path
from alembic import op
revision='semantic_0018'
down_revision='semantic_0017'
branch_labels=None
depends_on=None

def upgrade()->None:
    op.get_bind().exec_driver_sql(Path(__file__).with_name('semantic_0018_packet_snapshot.sql').read_text(),execution_options={'no_parameters':True})

def downgrade()->None:
    raise RuntimeError('destructive packet snapshot downgrade refused; rebuild a fresh database')
