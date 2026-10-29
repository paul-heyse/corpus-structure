"""Permit existing pure read helpers for canonical qualification projections."""

from alembic import op

revision = "semantic_0005"
down_revision = "semantic_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for signature in (
        "canonical_json(jsonb)",
        "value_meaning(text,text,text,text[],boolean)",
        "decimal_canonical(text)",
    ):
        op.execute(
            f"GRANT EXECUTE ON FUNCTION data.{signature} TO corpus_sem_reader,corpus_sem_writer"
        )


def downgrade() -> None:
    for signature in (
        "canonical_json(jsonb)",
        "value_meaning(text,text,text,text[],boolean)",
        "decimal_canonical(text)",
    ):
        op.execute(
            f"REVOKE EXECUTE ON FUNCTION data.{signature} FROM corpus_sem_reader,corpus_sem_writer"
        )
