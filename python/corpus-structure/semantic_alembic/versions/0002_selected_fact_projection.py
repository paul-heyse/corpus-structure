"""Declare the accepted-value projection over selected immutable fact identities.

This view does not own selection policy or semantic identity. It is rebuilt by migration.
"""

from alembic import op

revision = "semantic_0002"
down_revision = "semantic_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE VIEW data.selected_fact AS
        SELECT f.realization_id, f.release_id, f.fact_id, f.subject_id, f.property_id,
               f.object_value_id, f.qualification_value_id
        FROM data.fact AS f
        JOIN data.selection AS s
          ON s.realization_id = f.realization_id AND s.release_id = f.release_id
         AND s.fact_id = f.fact_id
    """)


def downgrade() -> None:
    op.execute("DROP VIEW data.selected_fact")
