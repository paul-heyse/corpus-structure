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

from typing import Annotated, Any

import typer
from pydantic import BaseModel
from rich.console import RenderableType
from rich.table import Table

from corpus_structure.cli.output import JsonOpt, emit, state
from corpus_structure.serve.database_description import DescriptionDepth
from corpus_structure.settings import DeploymentProfile

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


def _create(admin: Any, name: str, template: str, creation_token: str | None = None) -> bool:
    from sqlalchemy import create_engine, text

    from corpus_structure.core.db import extensions
    from corpus_structure.core.db.ownership import (
        DatabaseCreation,
        DatabaseReservation,
        stamp_owned,
    )

    try:
        creation = (
            DatabaseCreation(DatabaseReservation(name, creation_token))
            if creation_token is not None
            else None
        )
    except ValueError as error:
        raise DbRefused(str(error)) from error

    with admin.connect() as conn:
        encoding = conn.execute(text("SHOW server_encoding")).scalar()
        if str(encoding).upper() not in ("UTF8", "UTF-8"):
            raise DbRefused(f"the server encoding is {encoding}, not UTF-8: {extensions.PROVISION}")
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": name})
        if exists.scalar() is not None:
            if creation is not None:
                raise DbRefused(f"creation-only database already exists: {name!r}")
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
        if creation is not None:
            stamp_owned(conn, creation.acknowledge(conn))
    return True


def _migrate(
    engine: Any, name: str, created: bool, *, expected_predecessor: str | None = None
) -> DbReport:
    from sqlalchemy import text

    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID

    head = migrations.head_revision()
    with engine.begin() as conn:
        legacy = conn.execute(
            text(
                "SELECT to_regclass('meta.project') IS NOT NULL OR "
                "to_regclass('public.alembic_version') IS NOT NULL"
            )
        ).scalar_one()
        if legacy:
            raise DbRefused("legacy database refused: bootstrap a fresh owned semantic database")
        migrations.migration_fence(conn)
        current = migrations.current_revision(conn)
        if current != head and not created and expected_predecessor is None:
            local_development = name == "corpus_structure_dev" and conn.scalar(
                text("SELECT inet_server_addr() IS NULL AND current_setting('port') = '5434'")
            )
            if not local_development:
                raise DbRefused(
                    "use ci model change deploy for bound deployment; "
                    "database recovery requires --expected-predecessor"
                )
        applied = migrations.upgrade(
            conn, head or "head", expected_predecessor=expected_predecessor
        )
        current = migrations.current_revision(conn)
    return DbReport(
        database=name,
        created=created,
        revision=current,
        head=head,
        model_revision=PHYSICAL_MODEL_ID,
        applied=[str(a["revision"]) for a in applied],
    )


def _run(
    ctx: typer.Context,
    json_: bool,
    create: bool,
    creation_token: str | None = None,
    *,
    expected_predecessor: str | None = None,
) -> None:
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.core.db.extensions import ExtensionVersionMismatch

    settings = state(ctx).settings()
    from corpus_structure.semantic.migrations import MigrationPredecessorError
    from corpus_structure.semantic.runtime import connection_settings

    admin, engine, name = _engines(
        connection_settings(settings, "maintenance").database.sqlalchemy_url
    )
    try:
        with failure_boundary(
            json_,
            expected=(DbRefused, ExtensionVersionMismatch, MigrationPredecessorError),
            report_expected_validation=False,
        ):
            created = (
                _create(admin, name, settings.database.template, creation_token)
                if create
                else False
            )
            report = _migrate(engine, name, created, expected_predecessor=expected_predecessor)
    finally:
        admin.dispose()
        engine.dispose()
    emit(report, json=json_, render=_render)


@db_app.command("init")
def init(
    ctx: typer.Context,
    json_: JsonOpt = False,
    creation_token: str | None = typer.Option(
        None, "--creation-token", help="Require a new database and acknowledge its disposal owner."
    ),
) -> None:
    """Create the database from the template, check it and upgrade it to head."""
    _run(ctx, json_, create=True, creation_token=creation_token)


@db_app.command("migrate")
def migrate(
    ctx: typer.Context,
    expected_predecessor: Annotated[
        str | None, typer.Option(help="Require this installed revision for explicit recovery.")
    ] = None,
    json_: JsonOpt = False,
) -> None:
    """Upgrade the working development database or recover from an exact predecessor."""
    _run(ctx, json_, create=False, expected_predecessor=expected_predecessor)


@db_app.command("check")
def check_contract(
    ctx: typer.Context,
    release: Annotated[str, typer.Option("--release")],
    target: DeploymentProfile = "development",
    json_: JsonOpt = False,
) -> None:
    """Read-only native correspondence check for one explicitly archived release."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.managed import ResultError
    from corpus_structure.cli.target import select_target
    from corpus_structure.semantic.execution_admission import (
        ExecutionAdmissionError,
        admit_execution_release,
    )
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.releases import ReleaseConflict, open_release
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import (
        StorageTarget,
        acquired_target,
        verify_declared_route,
    )

    class ContractCheck(BaseModel):
        release_id: str
        execution_model_id: str | None
        physical_id: str
        target: DeploymentProfile
        acquired: StorageTarget

    with failure_boundary(json_, expected=(ExecutionAdmissionError, ReleaseConflict, ResultError)):
        selected, settings = select_target(ctx, target)
        with (
            open_runtime_engine(settings, "ci-db-check", purpose="read") as engine,
            read_snapshot(engine) as conn,
        ):
            if selected == "deployment":
                verify_declared_route(conn, settings)
            acquired = acquired_target(conn, purpose="read")
            try:
                prepared = open_release(conn, release)
            except KeyError as error:
                if error.args != (release,):
                    raise
                raise SemanticRefusal(f"unknown semantic release {release}") from error
            physical_id = admit_execution_release(prepared, connection=conn)
        emit(
            ContractCheck(
                release_id=prepared.release_id,
                execution_model_id=prepared.execution_model_id,
                physical_id=physical_id,
                target=selected,
                acquired=acquired,
            ),
            json=json_,
        )


@db_app.command(
    "describe",
    epilog=(
        "Example: ci db describe --schema data --depth columns "
        "--json\n\nDomain contract: [domain "
        "reader](docs/design/D8-agent-and-query-interfaces.md)"
    ),
)
def describe(
    ctx: typer.Context,
    schemas: Annotated[
        list[str],
        typer.Option(
            "--schema",
            help="Literal visible schema; repeat for multiple schemas.",
            rich_help_panel="Inputs",
        ),
    ],
    relations: Annotated[
        list[str] | None,
        typer.Option(
            "--relation",
            help="Literal relation name; repeat to select several.",
            rich_help_panel="Inputs",
        ),
    ] = None,
    depth: Annotated[
        DescriptionDepth, typer.Option("--depth", help="Deepest physical description level.")
    ] = DescriptionDepth.COLUMNS,
    estimates: Annotated[
        bool, typer.Option("--estimates", help="Include approximate catalog estimates.")
    ] = False,
    query: Annotated[
        str | None,
        typer.Option(
            "--query", help="Parameter-free SELECT; requires --release.", rich_help_panel="Inputs"
        ),
    ] = None,
    release: Annotated[str | None, typer.Option("--release")] = None,
    max_objects: Annotated[
        int, typer.Option(min=1, help="Maximum described objects.", rich_help_panel="Delivery")
    ] = 1000,
    max_columns: Annotated[
        int, typer.Option(min=1, help="Maximum described columns.", rich_help_panel="Delivery")
    ] = 10000,
    max_bytes: Annotated[
        int,
        typer.Option(min=1, help="Maximum description output bytes.", rich_help_panel="Delivery"),
    ] = 4 * 1024 * 1024,
    json_: JsonOpt = False,
) -> None:
    """Describe literal visible objects or an admitted parameter-free SELECT's output."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.database_description import (
        DatabaseDescriptionRequest,
        describe_database,
    )

    with failure_boundary(json_, expected=(ValueError,)):
        request = DatabaseDescriptionRequest(
            schemas=tuple(schemas),
            relations=tuple(relations or ()),
            depth=depth,
            estimates=estimates,
            query=query,
            release_id=release,
            max_objects=max_objects,
            max_columns=max_columns,
            max_bytes=max_bytes,
        )
        emit(describe_database(request, state(ctx).settings()), json=json_)


@db_app.command("status")
def status(
    ctx: typer.Context,
    maintenance: Annotated[
        bool, typer.Option(help="Read the private migration revision as the maintenance principal.")
    ] = False,
    target: DeploymentProfile = "development",
    json: JsonOpt = False,
) -> None:
    """Check database reachability and report the revision if visible."""
    from sqlalchemy import text

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.target import select_target
    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import (
        StorageTarget,
        acquired_target,
        verify_declared_route,
    )

    class DatabaseStatus(BaseModel):
        database: str
        principal: str
        server_version: str
        revision: str | None
        head: str | None
        revision_readable: bool
        target: DeploymentProfile
        acquired: StorageTarget

    from contextlib import ExitStack

    with failure_boundary(json, expected=(ValueError,)), ExitStack() as stack:
        selected, settings = select_target(ctx, target)
        purpose = "maintenance" if maintenance else "read"
        engine = stack.enter_context(
            open_runtime_engine(
                settings,
                "ci-db-status",
                purpose=purpose,
                timeout=5,
            )
        )
        conn = stack.enter_context(engine.connect())
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        if selected == "deployment":
            verify_declared_route(conn, settings)
        acquired = acquired_target(conn, purpose=purpose)
        database, principal, server_version = conn.execute(
            text("select current_database(), current_user, current_setting('server_version')")
        ).one()
        readable = bool(
            conn.scalar(
                text(
                    "select has_table_privilege("
                    "to_regclass('public.semantic_alembic_version'), 'SELECT')"
                )
            )
        )
        if maintenance and not readable:
            raise ValueError(
                "the configured maintenance principal cannot read the migration revision"
            )
        emit(
            DatabaseStatus(
                database=database,
                principal=principal,
                server_version=server_version,
                revision=migrations.current_revision(conn) if readable else None,
                revision_readable=readable,
                target=selected,
                acquired=acquired,
                head=migrations.head_revision(),
            ),
            json=json,
        )


def register(app: typer.Typer) -> None:
    app.add_typer(db_app, name="db")
