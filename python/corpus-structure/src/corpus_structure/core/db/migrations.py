"""Alembic linked to the model (model and projections §3.6; ADR-0022). `alembic/env.py` passes
`configure_kwargs()` to `context.configure`.

- **`template_args`** puts the installed model revision into `script.py.mako`, so each revision
  file states the model revision it realizes (`model_revision`, its content hash).
- **`process_revision_directives`** refuses to write a revision while the installed model revision
  is not registered in the revision log (`model/revisions.yaml`): a migration realizes a logged
  revision, never a working state. It raises `UnregisteredModelRevision`, a `CommandError`.
- **`on_version_apply`** records each applied step (revision, direction, the model revision its file
  states) in the Alembic config's `attributes["applied"]` and in the `corpus_structure.migrations`
  log.

`alembic.ext.checkconstraint_byname` (enabled in `env.py`) shows a CHECK change by name only,
which is why CHECK names carry the digest of their SQL (`schema/relational.py`).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from alembic.util import CommandError

from corpus_structure.core._model import revision

REVISIONS = Path(__file__).resolve().parents[2] / "model" / "revisions.yaml"
ALEMBIC_DIR = Path(__file__).resolve().parents[4] / "alembic"
LOG = logging.getLogger("corpus_structure.migrations")


class UnregisteredModelRevision(CommandError):
    """An Alembic revision was requested for a model revision the log does not hold."""


def registered(path: Path = REVISIONS) -> set[str]:
    """The content hashes the revision log holds."""
    entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return {str(entry["content_hash"]) for entry in entries}


def template_args() -> dict[str, str]:
    return {"model_revision": revision.CONTENT_HASH, "model_label": revision.LABEL}


def refusing_unregistered(
    path: Path = REVISIONS, current: str | None = None
) -> Callable[[Any, Any, list[Any]], None]:
    """A `process_revision_directives` hook over the log at `path` and model revision `current`."""

    def process_revision_directives(context: Any, rev: Any, directives: list[Any]) -> None:
        installed = revision.CONTENT_HASH if current is None else current
        if installed not in registered(path):
            raise UnregisteredModelRevision(
                f"model revision {installed[:12]} is not in {path.name}: record it "
                "(just model generate) before generating a migration for it"
            )

    return process_revision_directives


def on_version_apply(ctx: Any, step: Any, heads: set[str], run_args: dict[str, Any]) -> None:
    """Record an applied step (module doc)."""
    script = step.revision_map.get_revision(step.up_revision_id) if step.up_revision_id else None
    model_revision = getattr(getattr(script, "module", None), "model_revision", None)
    applied = {
        "revision": step.up_revision_id,
        "direction": "upgrade" if step.is_upgrade else "downgrade",
        "stamp": bool(step.is_stamp),
        "model_revision": model_revision,
    }
    environment = getattr(ctx, "environment_context", None)
    config = getattr(environment, "config", None)
    if config is not None:
        config.attributes.setdefault("applied", []).append(applied)
    LOG.info("applied %(direction)s %(revision)s (model revision %(model_revision)s)", applied)


def alembic_config(connection: Any = None) -> Any:
    """An Alembic config over the package's migrations; `connection` is used by `env.py`."""
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def head_revision() -> str | None:
    from alembic.script import ScriptDirectory

    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def current_revision(connection: Any) -> str | None:
    from alembic.migration import MigrationContext

    return MigrationContext.configure(connection).get_current_revision()


def upgrade(connection: Any, target: str = "head") -> list[dict[str, Any]]:
    """Upgrade the connection's database; the applied steps (`on_version_apply`'s records)."""
    from alembic import command

    config = alembic_config(connection)
    command.upgrade(config, target)
    return list(config.attributes.get("applied", []))


def downgrade(connection: Any, target: str = "base") -> None:
    from alembic import command

    command.downgrade(alembic_config(connection), target)


def configure_kwargs() -> dict[str, Any]:
    """The `context.configure` arguments that link Alembic to the model."""
    return {
        "template_args": template_args(),
        "process_revision_directives": refusing_unregistered(),
        "on_version_apply": [on_version_apply],
    }
