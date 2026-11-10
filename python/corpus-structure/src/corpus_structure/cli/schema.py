"""Compile semantic releases and explicitly author rollback-only native candidates."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

import typer
from pydantic import BaseModel
from rich.table import Table

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.managed import OperationAccount
from corpus_structure.cli.output import JsonOpt, diagnostic, emit
from corpus_structure.semantic.storage_target import StorageTarget

if TYPE_CHECKING:
    from sqlalchemy import MetaData

    from corpus_structure.cli.managed import Invocation
    from corpus_structure.semantic.native_objects import NativeIdentity


def model_stage(result: Invocation, name: str, **details: object) -> None:
    """Persist and announce an owner-named model phase."""
    result.stage(name, **details)
    diagnostic(f"Model {result.id} · {name}")


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
    ctx: typer.Context,
    domain: Annotated[list[str] | None, typer.Option("--domain")] = None,
    domains: Annotated[Path, typer.Option("--domains")] = Path("domains"),
    out: Annotated[Path | None, typer.Option("--out")] = None,
    json_: JsonOpt = False,
    retain_diagnostics: bool = False,
    correction_detail: bool = False,
    raw_evidence: bool = False,
    max_errors: int = 100,
    max_depth: int = 8,
    max_bytes: int = 262144,
    dependency_detail: bool = False,
    dependency_family: str | None = None,
    dependency_output: str | None = None,
    dependency_occurrence: str | None = None,
    dependency_after: int = 0,
    dependency_limit: int = 100,
):
    from corpus_structure.semantic.operation_reporting import projection_validation_report
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.regeneration import prepare_packs

    domain = domain or ["statistics"]
    from corpus_structure.cli.diagnostic_artifacts import diagnostic_scope, publish_diagnostic

    with diagnostic_scope(
        ctx,
        action="schema.compile",
        json=json_,
        retain=retain_diagnostics,
        detail=correction_detail,
        raw_evidence=raw_evidence,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
    ) as (failure, invocation):
        if any(Path(name).name != name for name in domain):
            raise SemanticRefusal("domain must name a pack under --domains")
        bundle, _deps, _profile, prepared = prepare_packs(tuple(domains / name for name in domain))
        failure.bind(prepared, "schema_compile")
        validation_model = projection_validation_report(
            prepared,
            detail=correction_detail,
            max_errors=max_errors,
            max_depth=max_depth,
            max_bytes=max_bytes,
            dependency_detail=dependency_detail,
            dependency_family=dependency_family,
            dependency_output=dependency_output,
            dependency_occurrence=dependency_occurrence,
            dependency_after=dependency_after,
            dependency_limit=dependency_limit,
        )
        if invocation is not None:
            validation_model = publish_diagnostic(invocation, validation_model)
        validation = validation_model.model_dump(mode="json")
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
                validation=validation,
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
    retain_diagnostics: bool = False,
    correction_detail: bool = False,
    raw_evidence: bool = False,
    max_errors: int = 100,
    max_depth: int = 8,
    max_bytes: int = 262144,
    dependency_detail: bool = False,
    dependency_family: str | None = None,
    dependency_output: str | None = None,
    dependency_occurrence: str | None = None,
    dependency_after: int = 0,
    dependency_limit: int = 100,
):
    """Check candidate packs or fully verify an archived release without changing it."""
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.refusals import SemanticRefusal

    if release is None:
        return compile_(
            ctx,
            domain or ["statistics"],
            domains,
            None,
            json_,
            retain_diagnostics=retain_diagnostics,
            correction_detail=correction_detail,
            raw_evidence=raw_evidence,
            max_errors=max_errors,
            max_depth=max_depth,
            max_bytes=max_bytes,
            dependency_detail=dependency_detail,
            dependency_family=dependency_family,
            dependency_output=dependency_output,
            dependency_occurrence=dependency_occurrence,
            dependency_after=dependency_after,
            dependency_limit=dependency_limit,
        )
    from corpus_structure.cli.diagnostic_artifacts import diagnostic_scope, publish_diagnostic
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.operation_reporting import projection_validation_report
    from corpus_structure.semantic.releases import verify_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    with diagnostic_scope(
        ctx,
        action="schema.check",
        json=json_,
        retain=retain_diagnostics,
        detail=correction_detail,
        raw_evidence=raw_evidence,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
    ) as (failure, invocation):
        if domain is not None:
            raise SemanticRefusal("select either --domain or --release")
        with (
            open_runtime_engine(state(ctx).settings(), "ci-schema-check", purpose="read") as engine,
            read_snapshot(engine) as conn,
        ):
            prepared = verify_release(conn, release)
            failure.bind(prepared, "schema_check")
        validation_model = projection_validation_report(
            prepared,
            detail=correction_detail,
            max_errors=max_errors,
            max_depth=max_depth,
            max_bytes=max_bytes,
            dependency_detail=dependency_detail,
            dependency_family=dependency_family,
            dependency_output=dependency_output,
            dependency_occurrence=dependency_occurrence,
            dependency_after=dependency_after,
            dependency_limit=dependency_limit,
        )
        if invocation is not None:
            validation_model = publish_diagnostic(invocation, validation_model)
        emit(
            CompileResult(
                packs=[],
                release_id=prepared.release_id,
                execution_model_id=prepared.execution_model_id,
                artifacts=[ArtifactRow(kind=a.kind, hash=a.digest) for a in prepared.artifacts],
                validation=validation_model.model_dump(mode="json"),
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
    result_id: str | None = None
    acquired_target: StorageTarget | None = None
    operation_account: OperationAccount | None = None


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
        "import pgvector.sqlalchemy\n"
        "from corpus_structure.semantic import alembic_native\n\n"
        "from corpus_structure.schema.relational import Vector\n\n"
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


def author_native_candidate(
    settings,
    authoring_database: str | None,
    predecessor_state: Path | None,
    *,
    expected_predecessor: str | None = None,
    expected_target: StorageTarget | None = None,
    target_metadata: MetaData | None = None,
    retire: frozenset[NativeIdentity] = frozenset(),
    recreate: frozenset[NativeIdentity] = frozenset(),
) -> tuple[NativeCandidateResult, dict[str, bytes]]:
    """Use the owned rollback-only authoring connection to prepare immutable product bytes."""
    from hashlib import sha256

    from sqlalchemy.engine import make_url

    from corpus_structure.semantic.alembic_native import NativeTransitionOp
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.migrations import current_revision, migration_fence
    from corpus_structure.semantic.native_candidate import (
        candidate_admission_sql,
        prepare_series_candidate,
        series_native_definitions,
    )
    from corpus_structure.semantic.native_objects import NativeAuthoringError
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.storage_target import (
        acquired_target,
        assert_explicit_route,
        verify_declared_route,
        verify_target,
    )

    source = make_url(settings.database.url)
    if authoring_database is None:
        authoring_database = source.database
    if authoring_database is None or authoring_database in {
        "",
        "postgres",
        "template0",
        "template1",
        settings.database.template,
    }:
        raise SemanticRefusal("native authoring requires a non-system, non-template database")
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
    if assert_explicit_route(selected)["dbname"] != authoring_database:
        raise SemanticRefusal("configured authoring database conflicts with its libpq route")
    target_metadata = metadata if target_metadata is None else target_metadata
    with (
        open_runtime_engine(selected, "ci-native-candidate", purpose="maintenance") as engine,
        engine.connect() as conn,
    ):
        transaction = conn.begin()
        try:
            verify_declared_route(conn, selected)
            target = (
                acquired_target(conn, purpose="maintenance")
                if expected_target is None
                else verify_target(conn, expected_target, purpose="maintenance")
            )
            migration_fence(conn)
            predecessor = current_revision(conn)
            if predecessor is None:
                raise SemanticRefusal("native authoring requires a migrated semantic database")
            if expected_predecessor is not None and predecessor != expected_predecessor:
                raise SemanticRefusal("native authoring predecessor differs from the preview")
            script, authoring = prepare_series_candidate(
                conn,
                owned_authoring=True,
                predecessor_state=predecessor_state,
                target_metadata=target_metadata,
                retire=retire,
                recreate=recreate,
            )
            upgrade_ops = script.upgrade_ops
            if upgrade_ops is None:
                raise NativeAuthoringError("single-connection candidate has no upgrade operations")
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
                retire=frozenset(item.identity for item in native if item.after is None),
                predecessor_state=predecessor_state,
                target_metadata=target_metadata,
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
    return NativeCandidateResult(
        database=authoring_database,
        predecessor=predecessor,
        output="",
        native_operations=len(native),
        ordinary_operations=len(upgrade_ops.ops) - len(native),
        acquired_target=target,
        products=[
            ArtifactRow(kind=name, hash=sha256(content).hexdigest())
            for name, content in products.items()
        ],
    ), products


def publish_native_candidate(result, report: NativeCandidateResult, products: dict[str, bytes]):
    directory = result.directory / "native-candidate"
    directory.mkdir()
    for name, content in products.items():
        (directory / name).write_bytes(content)
    result.publish("candidate", directory)
    return report.model_copy(update={"output": str(directory), "result_id": result.id})


@schema_app.command("native-candidate")
def native_candidate_(
    ctx: typer.Context,
    out: Annotated[Path | None, typer.Option("--out")] = None,
    authoring_database: Annotated[
        str | None,
        typer.Option(
            "--authoring-database",
            help="Rollback-only authoring database; defaults to the configured target.",
        ),
    ] = None,
    predecessor_state: Annotated[Path | None, typer.Option("--predecessor-state")] = None,
    intent: Annotated[
        Path | None, typer.Option(help="YAML retirement and recreation declaration.")
    ] = None,
    json_: JsonOpt = False,
):
    """Compare/render a managed native candidate with rollback-only maintenance authority."""
    import yaml

    from corpus_structure.cli.managed import ResultError, result_store
    from corpus_structure.cli.output import state
    from corpus_structure.schema.model import ModelError
    from corpus_structure.schema.model_change import NativeIntent, native_intent
    from corpus_structure.semantic.native_objects import NativeAuthoringError
    from corpus_structure.semantic.prepared_sql import SQLSyntaxError
    from corpus_structure.semantic.refusals import SemanticRefusal

    with refusal(
        json_,
        expected=(
            NativeAuthoringError,
            SQLSyntaxError,
            ResultError,
            ModelError,
            yaml.YAMLError,
            OSError,
        ),
    ):
        if out is not None and out.exists():
            raise SemanticRefusal("native authoring delivery requires a new directory")
        store = result_store(ctx)
        with store.operation("schema.native-candidate") as result:
            model_stage(result, "resolve native authoring intent")
            requested = (
                NativeIntent()
                if intent is None
                else NativeIntent.model_validate(yaml.safe_load(intent.read_bytes()))
            )
            retire, recreate = native_intent(requested.retire, requested.recreate)
            model_stage(result, "rollback-only authoring")
            report, products = author_native_candidate(
                state(ctx).settings(),
                authoring_database,
                predecessor_state,
                retire=retire,
                recreate=recreate,
            )
            model_stage(result, "publish native candidate")
            report = publish_native_candidate(result, report, products)
            result.settle(predecessor=report.predecessor, target=report.database)
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            delivered = store.deliver(result.id, "candidate", out)
            report = report.model_copy(update={"output": str(delivered)})
        emit(report, json=json_, render=_render_native_candidate)


@schema_app.command("explain-operation")
def explain_operation_(
    ctx: typer.Context,
    operation: str,
    release: Annotated[str, typer.Option("--release")],
    subject: Annotated[Path | None, typer.Option("--subject")] = None,
    dependency_detail: bool = False,
    dependency_family: str | None = None,
    dependency_output: str | None = None,
    dependency_occurrence: str | None = None,
    dependency_after: int = 0,
    dependency_limit: int = 100,
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
            report = explain_operation(
                prepared,
                operation,
                subject=reference,
                connection=conn,
                dependency_detail=dependency_detail,
                dependency_family=dependency_family,
                dependency_output=dependency_output,
                dependency_occurrence=dependency_occurrence,
                dependency_after=dependency_after,
                dependency_limit=dependency_limit,
            )
        emit(report, json=json_)


@schema_app.command("diff")
def diff_(
    ctx: typer.Context,
    before: str,
    after: str,
    source_run_id: int | None = None,
    review_run_id: int | None = None,
    review_cut_id: int | None = None,
    use_limit: int = 100,
    use_after: str | None = None,
    use_side: str = "before",
    dependency_detail: bool = False,
    dependency_family: str | None = None,
    dependency_output: str | None = None,
    dependency_occurrence: str | None = None,
    dependency_after: int = 0,
    dependency_limit: int = 100,
    json_: JsonOpt = False,
):
    """Explain declared semantic changes with unknown dependency coverage explicit."""
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.operation_reporting import compare_semantic_releases
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    with refusal(json_, expected=(SemanticRefusal, ValueError)) as failure:
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-semantic-diff", purpose="read"
            ) as engine,
            read_snapshot(engine) as conn,
        ):
            old, new = open_release(conn, before), open_release(conn, after)
            failure.bind(new, "compare_semantic_releases")
            report = compare_semantic_releases(
                old,
                new,
                connection=conn,
                source_run_id=source_run_id,
                review_run_id=review_run_id,
                review_cut_id=review_cut_id,
                use_limit=use_limit,
                use_after=use_after,
                use_side=use_side,
                dependency_detail=dependency_detail,
                dependency_family=dependency_family,
                dependency_output=dependency_output,
                dependency_occurrence=dependency_occurrence,
                dependency_after=dependency_after,
                dependency_limit=dependency_limit,
            )
        emit(report, json=json_)


def register(app: typer.Typer):
    app.add_typer(schema_app, name="schema")


@schema_app.command("inspect")
def inspect_contract_command(
    ctx: typer.Context,
    release: Annotated[str, typer.Option("--release")],
    subject_kind: Annotated[
        Literal["class", "property", "operation"], typer.Option("--subject-kind")
    ],
    subject: Annotated[str, typer.Option("--subject")],
    property_: Annotated[str | None, typer.Option("--property")] = None,
    view: Literal["summary", "detail"] = "summary",
    after: str | None = None,
    limit: Annotated[int, typer.Option(min=1, max=100)] = 20,
    input_: Annotated[Path | None, typer.Option("--input")] = None,
    validation_purpose: Literal["structural", "accepted"] | None = None,
    correction_detail: bool = False,
    raw_evidence: bool = False,
    max_errors: int = 100,
    max_depth: int = 8,
    max_bytes: int = 262144,
    json_: JsonOpt = False,
) -> None:
    """Inspect a selected archived contract; validate optional input without effects."""
    from corpus_structure.cli.output import state
    from corpus_structure.semantic.contract_inspection import inspect_contract
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.runtime import open_runtime_engine

    with refusal(json_, expected=(ValueError, OSError, KeyError)):
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-schema-inspect", purpose="read"
            ) as engine,
            read_snapshot(engine) as connection,
        ):
            prepared = open_release(connection, release)
            result = inspect_contract(
                prepared,
                subject_kind,
                subject,
                property=property_,
                view=view,
                after=after,
                limit=limit,
                input_json=input_.read_bytes() if input_ is not None else None,
                validation_purpose=validation_purpose,
                correction_detail=correction_detail,
                raw_evidence=raw_evidence,
                max_errors=max_errors,
                max_depth=max_depth,
                max_bytes=max_bytes,
            )

        def render(report):
            table = Table.grid()
            table.add_row(report.model_dump_json(indent=2))
            return table

        emit(result, json=json_, render=render)


@schema_app.command("diagnostic")
def inspect_diagnostic_command(
    ctx: typer.Context,
    result_id: str,
    raw_evidence: bool = False,
    max_bytes: int = 8 * 1024 * 1024,
    json_: JsonOpt = False,
):
    """Read retained correction evidence under its original immutable binding."""
    import json

    from corpus_structure.cli.diagnostic_artifacts import read_diagnostic
    from corpus_structure.cli.managed import result_boundary, result_store
    from corpus_structure.cli.output import write_report_text

    with result_boundary(json_):
        document = read_diagnostic(
            result_store(ctx), result_id, raw_evidence=raw_evidence, max_bytes=max_bytes
        )
        write_report_text(json.dumps(document, indent=None if json_ else 2) + "\n")
