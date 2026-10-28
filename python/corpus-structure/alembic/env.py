"""Alembic environment (store note §1).

- Schemas are included and filtered to the four D3 schemas; views are excluded from comparison.
- Server defaults are compared, and CHECK constraints by name (the opt-in plugin).
- One transaction per migration; `alembic_version` stays in `public`, so a downgrade that drops
  the four schemas keeps it.
- Tests pass their connection through `config.attributes["connection"]`; otherwise the URL comes
  from `Settings` (`CORPUS_DATABASE__URL`).
"""

from __future__ import annotations

from typing import Any

from alembic import context
from sqlalchemy import Connection, MetaData, create_engine, pool

from corpus_structure.settings import Settings

SCHEMAS = frozenset({"meta", "kb", "ops", "eval"})

# P0-F-4 sets this to the core.db metadata.
target_metadata: MetaData | None = None


def include_name(name: str | None, type_: str, parent_names: Any) -> bool:
    if type_ == "schema":
        return name in SCHEMAS
    return True


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    return not (type_ == "table" and getattr(obj, "info", {}).get("is_view", False))


def run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
        compare_server_default=True,
        autogenerate_plugins=["alembic.autogenerate.*", "alembic.ext.checkconstraint_byname"],
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    connection = context.config.attributes.get("connection")
    if connection is not None:
        run(connection)
        return
    engine = create_engine(Settings().database.sqlalchemy_url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            run(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise SystemExit("offline (--sql) migrations are not supported; run against a database")
run_online()
