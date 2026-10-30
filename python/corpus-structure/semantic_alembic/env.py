"""New physical realization only; the caller must explicitly supply a Connection."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from alembic import context

from corpus_structure.semantic.alembic_defaults import plugin as defaults_plugin
from corpus_structure.semantic.metadata import SCHEMAS, metadata
from corpus_structure.semantic.migrations import VERSION_TABLE


def include_name(name: str | None, type_: str, parent_names: Any) -> bool:
    return name in SCHEMAS if type_ == "schema" else True


def compare_default(
    ctx: Any,
    inspected: Any,
    declared: Any,
    inspected_default: str | None,
    metadata_default: Any,
    rendered_default: str | None,
) -> bool | None:
    """Avoid evaluating one volatile UUID default to compare it with itself.

    Other defaults retain Alembic's normal comparison, including changed expressions.
    """
    if (
        inspected.table.schema != "ops"
        or inspected.table.name != "task"
        or inspected.name != "invocation_key"
    ):
        return None

    def normalized(value: str | None) -> str:
        return (
            "".join((value or "").split())
            .replace("'legacy-task:'::text", "'legacy-task:'")
            .replace("(", "")
            .replace(")", "")
        )

    expected = "gen_random_uuid::text"
    if normalized(inspected_default) == normalized(rendered_default) == expected:
        return False
    return None


def applied(ctx: Any, step: Any, heads: Collection[Any], run_args: Mapping[str, Any]) -> None:
    context.config.attributes.setdefault("applied", []).append(
        {
            "revision": step.up_revision_id,
            "direction": "upgrade" if step.is_upgrade else "downgrade",
        }
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
    compare_server_default=compare_default,
    autogenerate_plugins=[
        "alembic.autogenerate.*",
        "alembic.ext.checkconstraint_byname",
        defaults_plugin.name,
    ],
    on_version_apply=applied,
)
with context.begin_transaction():
    context.run_migrations()
