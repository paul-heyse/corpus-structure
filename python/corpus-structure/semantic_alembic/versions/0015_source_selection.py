"""Enforce frozen source corpus, routing provenance and complete final cuts."""
from pathlib import Path
from alembic import op
revision='semantic_0015'
down_revision='semantic_0014'
branch_labels=None
depends_on=None

def upgrade()->None:
    op.get_bind().exec_driver_sql(Path(__file__).with_name('semantic_0015_source_selection.sql').read_text(),execution_options={'no_parameters':True})

def downgrade()->None:
    raise RuntimeError('destructive source selection downgrade refused; rebuild a fresh database')
