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
    return MigrationContext.configure(connection, opts={"version_table": VERSION_TABLE}).get_current_revision()


def upgrade(connection: Connection, target: str = "head") -> list[dict[str, Any]]:
    """Migrate on the caller's connection and transaction; never open a second connection."""
    config = alembic_config(connection)
    command.upgrade(config, target)
    return list(config.attributes.get("applied", []))


def downgrade(connection: Connection, target: str = "base") -> None:
    command.downgrade(alembic_config(connection), target)
