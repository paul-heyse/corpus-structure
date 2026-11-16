"""New physical realization only; the caller must explicitly supply a Connection."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

from corpus_structure.semantic.alembic_defaults import compare_default, compare_type
from corpus_structure.semantic.alembic_defaults import plugin as defaults_plugin
from corpus_structure.semantic.alembic_indexes import plugin as indexes_plugin
from corpus_structure.semantic.alembic_native import plugin as native_plugin
from corpus_structure.semantic.migrations import VERSION_TABLE


def run_migrations(context, *, use_default_metadata=True) -> None:
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
    if "target_metadata" in context.config.attributes:
        selected = context.config.attributes["target_metadata"]
    elif use_default_metadata:
        from corpus_structure.semantic.metadata import metadata

        selected = metadata
    else:
        # Frozen target upgrades need no current physical/compiler imports.
        # Autogeneration supplies its exact captured metadata explicitly.
        selected = None
    schemas = (
        {relation.schema for relation in selected.tables.values()}
        if selected is not None
        else set()
    )

    def include_name(name: str | None, type_: str, parent_names: Any) -> bool:
        return name in schemas if type_ == "schema" else True

    context.configure(
        connection=connection,
        target_metadata=selected,
        version_table=VERSION_TABLE,
        include_schemas=True,
        include_name=include_name,
        compare_server_default=compare_default,
        compare_type=compare_type,
        autogenerate_plugins=[
            "alembic.autogenerate.*",
            "alembic.ext.checkconstraint_byname",
            defaults_plugin.name,
            indexes_plugin.name,
            native_plugin.name,
        ],
        native_authoring=context.config.attributes.get("native_authoring"),
        on_version_apply=applied,
    )
    with context.begin_transaction():
        context.run_migrations()
