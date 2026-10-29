"""Alembic environment (store note §1).

- The target is the generated `MetaData` with the overlay (`core.db.metadata`). Schemas are filtered
  to the four D3 schemas; views (`Table.is_view`) and the overlay's deferred tables (`kb.embedding`,
  phase 1) are excluded from comparison.
- Server defaults are compared (the `regconfig` default is cast in the model's projection, so
  the server-side comparison does not fail with 22P02, probe Q-3), and CHECK constraints by name
  (the opt-in plugin).
- Linked to the model (`core/db/migrations.py`): each revision file states its model revision, a
  revision for an unlogged model revision is refused, and applied steps are recorded.
- One transaction per migration; `alembic_version` stays in `public`, so a downgrade that drops
  the four schemas keeps it.
- Tests pass their connection through `config.attributes["connection"]`; otherwise the URL comes
  from `Settings` (`CORPUS_DATABASE__URL`).
"""

from __future__ import annotations

from typing import Any

from alembic import context
from sqlalchemy import Connection, MetaData, create_engine, pool
from sqlalchemy.dialects.postgresql import REGCONFIG, base

from corpus_structure.core import db
from corpus_structure.core.db import migrations
from corpus_structure.settings import Settings

SCHEMAS = frozenset({"meta", "kb", "ops", "eval"})
# reflection knows regconfig, so autogenerate compares its type instead of warning
names: dict[str, Any] = base.ischema_names
names.setdefault("regconfig", REGCONFIG)

target_metadata: MetaData = db.metadata


def include_name(name: str | None, type_: str, parent_names: Any) -> bool:
    if type_ == "schema":
        return name in SCHEMAS
    return True


def include_object(
    obj: Any, name: str | None, type_: str, reflected: bool, compare_to: Any
) -> bool:
    if type_ != "table":
        return True
    info = getattr(obj, "info", {})
    return not (getattr(obj, "is_view", False) or info.get("is_view") or info.get("deferred"))


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
        # the model linkage: template_args, the unregistered-revision refusal, on_version_apply
        **migrations.configure_kwargs(),
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
