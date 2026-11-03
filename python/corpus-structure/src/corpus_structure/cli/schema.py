"""Compile semantic releases and explicitly author rollback-only native candidates."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.table import Table

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, emit


def refusal(json, *, expected=(), context=None):
    from corpus_structure.semantic.execution_admission import ExecutionAdmissionError
    from corpus_structure.semantic.releases import ReleaseConflict
    from corpus_structure.semantic.types import PreparationError

    return failure_boundary(
        json,
        expected=(PreparationError, ReleaseConflict, ExecutionAdmissionError, *expected),
        context=context,
    )


schema_app = typer.Typer(help="Compile a composed semantic release.", no_args_is_help=True)


class ArtifactRow(BaseModel):
    kind: str
    hash: str


class CompileResult(BaseModel):
    packs: list[str]
    release_id: str
    execution_model_id: str | None
    artifacts: list[ArtifactRow]
    validation: dict | None = None


def _render(result):
    table = Table("kind", "hash", title=f"semantic release {result.release_id}")
    for artifact in result.artifacts:
        table.add_row(artifact.kind, artifact.hash)
    return table


@schema_app.command("compile")
def compile_(
    domain: Annotated[list[str] | None, typer.Option("--domain")] = None,
    domains: Annotated[Path, typer.Option("--domains")] = Path("domains"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
    json_: JsonOpt = False,
):
    from corpus_structure.semantic.operation_reporting import projection_validation_report
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.regeneration import prepare_packs

    domain = domain or ["statistics"]
    with refusal(json_):
        if any(Path(name).name != name for name in domain):
            raise SemanticRefusal("domain must name a pack under --domains")
        bundle, _deps, _profile, prepared = prepare_packs(tuple(domains / name for name in domain))
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
            (out / "manifest.json").write_bytes(prepared.manifest)
            for artifact in prepared.artifacts:
                (out / (artifact.kind.replace("/", "_") + ".artifact")).write_bytes(
                    artifact.content
                )
            for source in bundle.sources:
                target = out / "sources" / (source.name.replace("/", "_") + ".yaml")
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(source.content)
        emit(
            CompileResult(
                packs=domain,
                release_id=prepared.release_id,
                execution_model_id=prepared.execution_model_id,
                artifacts=[ArtifactRow(kind=a.kind, hash=a.digest) for a in prepared.artifacts],
                validation=projection_validation_report(prepared).model_dump(mode="json"),
            ),
            json=json_,
            render=_render,
        )


@schema_app.command("check")
def check_(
    ctx: typer.Context,
    domain: Annotated[list[str] | None, typer.Option("--domain")] = None,
    release: Annotated[str | None, typer.Option("--release")] = None,
    domains: Annotated[Path, typer.Option("--domains")] = Path("domains"),
    json_: JsonOpt = False,
):
    """Check candidate packs or fully verify an archived release without changing it."""
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.refusals import SemanticRefusal

    if release is None:
        return compile_(domain or ["statistics"], domains, None, json_)
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.operation_reporting import projection_validation_report
    from corpus_structure.semantic.releases import verify_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    with refusal(json_) as failure:
        if domain is not None:
            raise SemanticRefusal("select either --domain or --release")
        with (
            open_runtime_engine(state(ctx).settings(), "ci-schema-check", purpose="read") as engine,
            read_snapshot(engine) as conn,
        ):
            prepared = verify_release(conn, release)
            failure.bind(prepared, "schema_check")
        emit(
            CompileResult(
                packs=[],
                release_id=prepared.release_id,
                execution_model_id=prepared.execution_model_id,
                artifacts=[ArtifactRow(kind=a.kind, hash=a.digest) for a in prepared.artifacts],
                validation=projection_validation_report(prepared).model_dump(mode="json"),
            ),
            json=json_,
            render=_render,
        )


@schema_app.command("derive")
def derive_(
    out: Annotated[Path, typer.Option("--out")],
    domain: Annotated[list[str] | None, typer.Option("--domain")] = None,
    domains: Annotated[Path, typer.Option("--domains")] = Path("domains"),
    json_: JsonOpt = False,
):
    """Export composed model artifacts; use native-candidate for native authoring."""
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.regeneration import prepare_packs

    with refusal(json_):
        if out.exists():
            raise SemanticRefusal("derivation requires a new --out directory")
        selected = domain or ["statistics"]
        if any(Path(name).name != name for name in selected):
            raise SemanticRefusal("domain must name a pack under --domains")
        bundle, _deps, _profile, prepared = prepare_packs(
            tuple(domains / name for name in selected)
        )
        out.mkdir(parents=True)
        (out / "manifest.json").write_bytes(prepared.manifest)
        for artifact in prepared.artifacts:
            (out / (artifact.kind.replace("/", "_") + ".artifact")).write_bytes(artifact.content)
        (out / "sources").mkdir()
        for source in bundle.sources:
            (out / "sources" / (source.name.replace("/", "_") + ".yaml")).write_bytes(
                source.content
            )
        emit(
            CompileResult(
                packs=selected,
                release_id=prepared.release_id,
                execution_model_id=prepared.execution_model_id,
                artifacts=[ArtifactRow(kind=a.kind, hash=a.digest) for a in prepared.artifacts],
            ),
            json=json_,
            render=_render,
        )


class NativeCandidateResult(BaseModel):
    database: str
    predecessor: str
    output: str
    native_operations: int
    ordinary_operations: int
    products: list[ArtifactRow]


def _render_native_candidate(result):
    table = Table("field", "value", title="native candidate")
    for key in ("database", "predecessor", "output", "native_operations", "ordinary_operations"):
        table.add_row(key, str(getattr(result, key)))
    return table


def _native_candidate_python(upgrade_ops, restore_sql: str) -> str:
    """Render role restoration against the upgrade caller, never the authoring login."""
    import ast

    from alembic.autogenerate import render_python_code

    source = (
        "from alembic import op\nimport sqlalchemy as sa\n"
        "from sqlalchemy import Text\nfrom sqlalchemy.dialects import postgresql\n"
        "from corpus_structure.semantic import alembic_native\n\n"
        "def upgrade():\n" + render_python_code(upgrade_ops) + "\n"
    )
    module = ast.parse(source)
    function = next(item for item in module.body if isinstance(item, ast.FunctionDef))

    class RestoreRole(ast.NodeTransformer):
        def visit_Call(self, node: ast.Call) -> ast.AST:
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "op"
                and node.func.attr == "execute"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == restore_sql
            ):
                return ast.parse(
                    'op.execute("SET LOCAL ROLE " + '
                    "op.get_bind().dialect.identifier_preparer.quote(_migration_role))",
                    mode="eval",
                ).body
            return self.generic_visit(node)

    RestoreRole().visit(function)
    function.body.insert(
        0,
        ast.parse(
            '_migration_role = op.get_bind().exec_driver_sql("SELECT current_user").scalar_one()'
        ).body[0],
    )
    return ast.unparse(ast.fix_missing_locations(module)) + "\n"


@schema_app.command("native-candidate")
def native_candidate_(
    ctx: typer.Context,
    authoring_database: Annotated[
        str,
        typer.Option(
            "--authoring-database",
            help="Explicitly owned disposable semantic database for rollback-only authoring.",
        ),
    ],
    out: Annotated[Path, typer.Option("--out")],
    predecessor_state: Annotated[Path | None, typer.Option("--predecessor-state")] = None,
    json_: JsonOpt = False,
):
    """Compare/render a native candidate on an owned maintenance connection; never deploy it."""
    from hashlib import sha256
    from tempfile import TemporaryDirectory

    from sqlalchemy.engine import make_url

    from corpus_structure.cli.output import state
    from corpus_structure.semantic.alembic_native import NativeTransitionOp
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.migrations import current_revision
    from corpus_structure.semantic.native_candidate import (
        candidate_admission_sql,
        prepare_series_candidate,
        series_native_definitions,
    )
    from corpus_structure.semantic.native_objects import NativeAuthoringError
    from corpus_structure.semantic.prepared_sql import SQLSyntaxError
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.companion_export import _publish_directory

    with refusal(json_, expected=(NativeAuthoringError, SQLSyntaxError)):
        if out.exists():
            raise SemanticRefusal("native authoring requires a new --out directory")
        settings = state(ctx).settings()
        source = make_url(settings.database.url)
        if authoring_database in {
            "",
            "postgres",
            "template0",
            "template1",
            source.database,
            settings.database.template,
        }:
            raise SemanticRefusal("select a separate explicitly owned --authoring-database")
        maintenance = make_url(settings.database.maintenance_url).set(database=authoring_database)
        selected = settings.model_copy(
            update={
                "database": settings.database.model_copy(
                    update={
                        "url": source.set(database=authoring_database).render_as_string(
                            hide_password=False
                        ),
                        "maintenance_url": maintenance.render_as_string(hide_password=False),
                    }
                )
            }
        )
        with (
            open_runtime_engine(selected, "ci-native-candidate", purpose="maintenance") as engine,
            engine.connect() as conn,
        ):
            transaction = conn.begin()
            try:
                predecessor = current_revision(conn)
                if predecessor is None:
                    raise SemanticRefusal("native authoring requires a migrated semantic database")
                script, authoring = prepare_series_candidate(
                    conn, owned_authoring=True, predecessor_state=predecessor_state
                )
                upgrade_ops = script.upgrade_ops
                if upgrade_ops is None:
                    raise NativeAuthoringError(
                        "single-connection candidate has no upgrade operations"
                    )
                native = [item for item in upgrade_ops.ops if isinstance(item, NativeTransitionOp)]
                migration_role = conn.exec_driver_sql("SELECT current_user").scalar_one()
                python_source = _native_candidate_python(
                    upgrade_ops,
                    "SET LOCAL ROLE " + conn.dialect.identifier_preparer.quote(migration_role),
                )
                compile(python_source, "native_candidate.py", "exec")
                admission = candidate_admission_sql(
                    conn,
                    series_native_definitions(conn),
                    authoring.desired,
                    predecessor_state=predecessor_state,
                )
                products = {
                    "native_candidate.py": python_source.encode(),
                    "native_operations.json": canonical_bytes(
                        {
                            "version": 1,
                            "predecessor": predecessor,
                            "operations": [item.payload() for item in native],
                            "desired": [item.payload() for item in authoring.desired],
                        }
                    ),
                    "native_admission.sql": admission.encode(),
                }
            finally:
                transaction.rollback()
        out.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".native-candidate-", dir=out.parent) as directory:
            prepared_output = Path(directory) / "candidate"
            prepared_output.mkdir()
            for name, content in products.items():
                (prepared_output / name).write_bytes(content)
            _publish_directory(prepared_output, out)
        emit(
            NativeCandidateResult(
                database=authoring_database,
                predecessor=predecessor,
                output=str(out),
                native_operations=len(native),
                ordinary_operations=len(upgrade_ops.ops) - len(native),
                products=[
                    ArtifactRow(kind=name, hash=sha256(content).hexdigest())
                    for name, content in products.items()
                ],
            ),
            json=json_,
            render=_render_native_candidate,
        )


@schema_app.command("explain-operation")
def explain_operation_(
    ctx: typer.Context,
    operation: str,
    release: Annotated[str, typer.Option("--release")],
    subject: Annotated[Path | None, typer.Option("--subject")] = None,
    json_: JsonOpt = False,
):
    """Explain a declared operation; an observation never authorizes later effects."""
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.operation_reporting import (
        explain_operation,
        parse_operation_subject,
    )
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    with refusal(json_, expected=(SemanticRefusal, ValueError, OSError)) as failure:
        raw_subject = subject.read_bytes() if subject is not None else None
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-explain-operation", purpose="read"
            ) as engine,
            read_snapshot(engine) as conn,
        ):
            prepared = open_release(conn, release)
            failure.bind(prepared, operation)
            reference = (
                parse_operation_subject(prepared, operation, raw_subject, connection=conn)
                if raw_subject is not None
                else None
            )
            report = explain_operation(prepared, operation, subject=reference, connection=conn)
        emit(report, json=json_)


@schema_app.command("diff")
def diff_(ctx: typer.Context, before: str, after: str, json_: JsonOpt = False):
    """Explain declared semantic changes with unknown dependency coverage explicit."""
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.operation_reporting import compare_semantic_releases
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    with refusal(json_, expected=(SemanticRefusal,)) as failure:
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-semantic-diff", purpose="read"
            ) as engine,
            read_snapshot(engine) as conn,
        ):
            old, new = open_release(conn, before), open_release(conn, after)
            failure.bind(new, "compare_semantic_releases")
            report = compare_semantic_releases(old, new)
        emit(report, json=json_)


def register(app: typer.Typer):
    app.add_typer(schema_app, name="schema")
