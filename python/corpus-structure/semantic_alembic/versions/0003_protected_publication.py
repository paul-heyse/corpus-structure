"""Deploy frozen protected publication routines and privileges in the migration transaction.

The companion is historical deployment output, not an import of evolving application code.
Future routine changes need an explicit new revision. Rebuild a fresh realization to reverse.
"""

from pathlib import Path
from unicodedata import unidata_version

from alembic import op

revision = "semantic_0003"
physical_model_id = "physical:f58ffa92ea042f73bf2aba9da93286fd43de1da8d72953a75b60645cbda05370"
down_revision = "semantic_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if (
        unidata_version != "16.0.0"
        or conn.exec_driver_sql("SELECT pg_catalog.unicode_version()").scalar_one() != "16.0"
    ):
        raise RuntimeError("semantic publication requires qualified Unicode 16 casefold")
    database = conn.dialect.identifier_preparer.quote(
        conn.exec_driver_sql("SELECT current_database()").scalar_one()
    )
    source = Path(__file__).with_name("semantic_0003_publication.sql").read_text()
    conn.exec_driver_sql(
        source.replace("__semantic_database__", database),
        execution_options={"no_parameters": True},
    )


def downgrade() -> None:
    raise RuntimeError(
        "destructive semantic publication downgrade refused; rebuild a fresh database"
    )
