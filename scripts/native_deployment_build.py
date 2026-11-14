"""Construct a semantic deployment on a caller-owned connection.

Database identities, leases, publication and cleanup belong to PgAdmin. This module's
dependencies describe construction inputs independently of fixture and receipt orchestration.
"""

from sqlalchemy import Connection, text

from corpus_structure.core.db import extensions
from corpus_structure.semantic.migrations import upgrade


def construct_deployment(connection: Connection) -> None:
    extensions.check(connection.execute(text(extensions.FOUND)).all())
    if connection.execute(
        text("SELECT 1 FROM pg_namespace WHERE nspname IN ('sem','data','kb','meta')")
    ).first():
        raise RuntimeError("semantic deployment construction requires an empty namespace")
    upgrade(connection)
