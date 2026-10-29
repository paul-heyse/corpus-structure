"""New physical realization only; the caller must explicitly supply a Connection."""

from __future__ import annotations

from typing import Any

from alembic import context

from corpus_structure.semantic.metadata import SCHEMAS, metadata
from corpus_structure.semantic.migrations import VERSION_TABLE


def include_name(name: str | None, type_: str, parent_names: Any) -> bool:
    return name in SCHEMAS if type_ == "schema" else True


def applied(ctx: Any, step: Any, heads: set[str], run_args: dict[str, Any]) -> None:
    context.config.attributes.setdefault("applied", []).append(
        {"revision": step.up_revision_id, "direction": "upgrade" if step.is_upgrade else "downgrade"}
    )


if context.is_offline_mode():
    raise RuntimeError("semantic migrations require an explicit live Connection")
connection = context.config.attributes.get("connection")
if connection is None:
    raise RuntimeError("semantic migrations require Config.attributes['connection']")
context.configure(
    connection=connection,
    target_metadata=metadata,
    version_table=VERSION_TABLE,
    include_schemas=True,
    include_name=include_name,
    compare_server_default=True,
    autogenerate_plugins=["alembic.autogenerate.*", "alembic.ext.checkconstraint_byname"],
    on_version_apply=[applied],
)
with context.begin_transaction():
    context.run_migrations()
