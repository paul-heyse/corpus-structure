from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql
from corpus_structure.semantic import alembic_native

def upgrade():
    _migration_role = op.get_bind().exec_driver_sql('SELECT current_user').scalar_one()
    pass
