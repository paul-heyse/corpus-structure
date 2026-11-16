"""The existing semantic migration tree; explicit caller-owned connection only."""

from alembic import context

from corpus_structure.semantic.alembic_environment import run_migrations

run_migrations(context)
