"""Explicit semantic migration target, isolated from the frozen knowledge-schema history."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection

ALEMBIC_DIR = Path(__file__).resolve().parents[3] / "semantic_alembic"
VERSION_TABLE = "semantic_alembic_version"


def alembic_config(connection: Connection | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def head_revision() -> str | None:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def current_revision(connection: Connection) -> str | None:
    return MigrationContext.configure(
        connection, opts={"version_table": VERSION_TABLE}
    ).get_current_revision()


class MigrationPredecessorError(ValueError):
    """An explicit migration target does not have the expected current predecessor."""


def migration_fence(connection: Connection) -> None:
    """Serialize migration effects on the same PostgreSQL database for this transaction."""
    connection.exec_driver_sql(
        "SELECT pg_advisory_xact_lock(hashtextextended('corpus-structure semantic migrations', 0))"
    )


def upgrade(
    connection: Connection, target: str = "head", *, expected_predecessor: str | None = None
) -> list[dict[str, Any]]:
    """Migrate on the caller's connection and transaction; never open a second connection."""
    migration_fence(connection)
    if expected_predecessor is not None:
        actual = current_revision(connection)
        if actual == target:
            return []
        if actual != expected_predecessor:
            raise MigrationPredecessorError(
                f"expected native predecessor {expected_predecessor}, found {actual}"
            )
    config = alembic_config(connection)
    command.upgrade(config, target)
    return list(config.attributes.get("applied", []))


def downgrade(connection: Connection, target: str = "base") -> None:
    if target == "base":
        # Refuse before an earlier revision's reversible projection has been dropped.
        raise RuntimeError(
            "semantic bootstrap downgrade is destructive; rebuild the owned realization"
        )
    migration_fence(connection)
    command.downgrade(alembic_config(connection), target)
