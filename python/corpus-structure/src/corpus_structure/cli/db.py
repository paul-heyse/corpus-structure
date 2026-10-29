"""`ci db init` and `ci db migrate` (foundations §3.8, P0-F-4; D3 §13).

Both report the database, its revision after the command, the migrations' head and the installed
model revision, with `--json`.
- `init` creates the configured database `TEMPLATE <database.template>` on an autocommit connection
  to `postgres`, unless it exists. It first checks that the server encoding is UTF-8 (offsets are
  code points on both sides only then) and that the template's extensions are at the versions of
  `ops/postgresql/extensions.txt`; then it upgrades to head.
- `migrate` upgrades an existing database to head.
A failed check exits with code 1, its reason and D3 §13's instruction on stderr.
"""

from __future__ import annotations

from typing import Any

import typer
from pydantic import BaseModel
from rich.console import RenderableType
from rich.table import Table

from corpus_structure.cli.output import JsonOpt, emit, state, stderr_console

db_app = typer.Typer(help="Create or migrate the database.", no_args_is_help=True)


class DbReport(BaseModel):
    database: str
    created: bool
    revision: str | None
    head: str | None
    model_revision: str
    applied: list[str]


class DbRefused(RuntimeError):
    pass


def _render(result: BaseModel) -> RenderableType:
    assert isinstance(result, DbReport)
    table = Table("field", "value", title="database")
    for name, value in result.model_dump(mode="json").items():
        table.add_row(name, ", ".join(value) if isinstance(value, list) else str(value))
    return table


def _engines(url: str) -> tuple[Any, Any, str]:
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from sqlalchemy.pool import NullPool

    target = make_url(url)
    name = str(target.database)
    admin = create_engine(
        target.set(database="postgres"), poolclass=NullPool, isolation_level="AUTOCOMMIT"
    )
    return admin, create_engine(target, poolclass=NullPool), name


def _quote(name: str) -> str:
    import re

    if not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
        raise DbRefused(f"unexpected database name {name!r}")
    return f'"{name}"'


def _create(admin: Any, name: str, template: str) -> bool:
    from sqlalchemy import create_engine, text

    from corpus_structure.core.db import extensions

    with admin.connect() as conn:
        encoding = conn.execute(text("SHOW server_encoding")).scalar()
        if str(encoding).upper() not in ("UTF8", "UTF-8"):
            raise DbRefused(f"the server encoding is {encoding}, not UTF-8: {extensions.PROVISION}")
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name})
        if exists.scalar() is not None:
            return False
        found = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": template})
        if found.scalar() is None:
            raise DbRefused(f"the template {template!r} is missing: {extensions.PROVISION}")
    probe = create_engine(admin.url.set(database=template), isolation_level="AUTOCOMMIT")
    try:
        with probe.connect() as conn:
            extensions.check(
                [
                    (str(name), str(version))
                    for name, version in conn.execute(text(extensions.FOUND))
                ]
            )
    finally:
        probe.dispose()  # a template must have no connection while it is cloned
    with admin.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {_quote(name)} TEMPLATE {_quote(template)}"))
    return True


def _migrate(engine: Any, name: str, created: bool) -> DbReport:
    from sqlalchemy import text

    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID

    with engine.begin() as conn:
        legacy = conn.execute(
            text(
                "SELECT to_regclass('meta.project') IS NOT NULL OR "
                "to_regclass('public.alembic_version') IS NOT NULL"
            )
        ).scalar_one()
        if legacy:
            raise DbRefused("legacy database refused: bootstrap a fresh owned semantic database")
        applied = migrations.upgrade(conn)
        current = migrations.current_revision(conn)
    return DbReport(
        database=name,
        created=created,
        revision=current,
        head=migrations.head_revision(),
        model_revision=PHYSICAL_MODEL_ID,
        applied=[str(a["revision"]) for a in applied],
    )


def _run(ctx: typer.Context, json_: bool, create: bool) -> None:
    from sqlalchemy.exc import OperationalError

    from corpus_structure.core.db.extensions import ExtensionVersionMismatch

    settings = state(ctx).settings()
    from corpus_structure.semantic.runtime import connection_settings

    admin, engine, name = _engines(
        connection_settings(settings, "maintenance").database.sqlalchemy_url
    )
    try:
        created = _create(admin, name, settings.database.template) if create else False
        report = _migrate(engine, name, created)
    except (DbRefused, ExtensionVersionMismatch) as error:
        stderr_console().print(str(error))
        raise typer.Exit(code=1) from None
    except OperationalError as error:
        reason = str(error.orig or error).strip().splitlines()[0]
        stderr_console().print(f"cannot reach the database ({reason}); see D3 §13")
        raise typer.Exit(code=1) from None
    finally:
        admin.dispose()
        engine.dispose()
    emit(report, json=json_, render=_render)


@db_app.command("init")
def init(ctx: typer.Context, json_: JsonOpt = False) -> None:
    """Create the database from the template, check it and upgrade it to head."""
    _run(ctx, json_, create=True)


@db_app.command("migrate")
def migrate(ctx: typer.Context, json_: JsonOpt = False) -> None:
    """Upgrade a semantic database; refuse the retired legacy history."""
    _run(ctx, json_, create=False)


def register(app: typer.Typer) -> None:
    app.add_typer(db_app, name="db")
