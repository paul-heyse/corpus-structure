"""Fresh current target revisions use the same explicit Alembic lifecycle."""

from alembic import context

from corpus_structure.semantic.alembic_environment import run_migrations

run_migrations(context)
