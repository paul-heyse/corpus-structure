"""Compile semantic releases and explicitly author rollback-only native candidates."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

import typer
from pydantic import BaseModel
from rich.table import Table

from corpus_structure.cli.declarations import (
    ContractInput,
    ContractKindOption,
    ContractLimit,
    ContractViewOption,
    CorrectionBytes,
    CorrectionDepth,
    CorrectionDetail,
    CorrectionErrors,
    DependencyAfter,
    DependencyDetail,
    DependencyFamily,
    DependencyLimit,
    DependencyOccurrence,
    DependencyOutput,
    DiagnosticBytes,
    Domain,
    Domains,
    RawEvidence,
    RetainDiagnostics,
    ValidationPurposeOption,
)
from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.managed import OperationAccount
from corpus_structure.cli.output import JsonOpt, diagnostic, emit
from corpus_structure.cli.target import ConfiguredSelection, current_selection, selection_summary
from corpus_structure.semantic.migration_chain import NativeMigrationBase
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


@schema_app.command(
    "compile",
    epilog=(
        "Example: ci schema compile --domain statistics "
        "--correction-detail --json\n\nDomain contract: [domain "
        "reader](docs/design/D2-schema-and-guidelines.md)"
    ),
)
def compile_(
    ctx: typer.Context,
    domain: Domain = None,
    domains: Domains = Path("domains"),
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Artifact output directory.", rich_help_panel="Delivery"),
    ] = None,
    json_: JsonOpt = False,
    retain_diagnostics: RetainDiagnostics = False,
    correction_detail: CorrectionDetail = False,
    raw_evidence: RawEvidence = False,
    max_errors: CorrectionErrors = 100,
    max_depth: CorrectionDepth = 8,
    max_bytes: CorrectionBytes = 262144,
    dependency_detail: DependencyDetail = False,
    dependency_family: DependencyFamily = None,
    dependency_output: DependencyOutput = None,
    dependency_occurrence: DependencyOccurrence = None,
    dependency_after: DependencyAfter = 0,
    dependency_limit: DependencyLimit = 100,
):
    """Prepare composed packs and optionally write artifacts; never admit or select a release."""
    _compile_packs(
        ctx,
        domain,
        domains,
        out,
        json_,
        action="schema.compile",
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


def _compile_packs(
    ctx,
    domain,
    domains,
    out,
    json_,
    *,
    action,
    retain_diagnostics,
    correction_detail,
    raw_evidence,
    max_errors,
    max_depth,
    max_bytes,
    dependency_detail,
    dependency_family,
    dependency_output,
    dependency_occurrence,
    dependency_after,
    dependency_limit,
):
    from corpus_structure.semantic.operation_reporting import projection_validation_report
    from corpus_structure.semantic.regeneration import acquire_packs, prepare_release

    domain = domain or ["statistics"]
    from corpus_structure.cli.diagnostic_artifacts import (
        diagnostic_scope,
        retain_optional_diagnostic,
    )

    with diagnostic_scope(
        ctx,
        action=action,
        json=json_,
        retain=retain_diagnostics,
        detail=correction_detail,
        raw_evidence=raw_evidence,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
    ) as (failure, invocation):
        bundle, _deps, _profile = acquire_packs(tuple(domains / name for name in domain))
        failure.sources = bundle.sources
        prepared = prepare_release(bundle, _deps, _profile)
        failure.bind(prepared, action.replace(".", "_"))
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
        validation_model = retain_optional_diagnostic(invocation, validation_model, context=failure)
        # A supplied success report always survives optional custody.
        assert validation_model is not None
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


@schema_app.command(
    "check",
    epilog=(
        "Example: ci schema check --domain statistics "
        "--retain-diagnostics --json\n\nDomain contract: [domain "
        "reader](docs/design/D2-schema-and-guidelines.md)"
    ),
)
def check_(
    ctx: typer.Context,
    domain: Domain = None,
    release: Annotated[
        str | None,
        typer.Option("--release", help="Archived semantic release ID.", rich_help_panel="Inputs"),
    ] = None,
    domains: Domains = Path("domains"),
    json_: JsonOpt = False,
    retain_diagnostics: RetainDiagnostics = False,
    correction_detail: CorrectionDetail = False,
    raw_evidence: RawEvidence = False,
    max_errors: CorrectionErrors = 100,
    max_depth: CorrectionDepth = 8,
    max_bytes: CorrectionBytes = 262144,
    dependency_detail: DependencyDetail = False,
    dependency_family: DependencyFamily = None,
    dependency_output: DependencyOutput = None,
    dependency_occurrence: DependencyOccurrence = None,
    dependency_after: DependencyAfter = 0,
    dependency_limit: DependencyLimit = 100,
):
    """Check candidate packs or fully verify an archived release without changing it."""
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.refusals import SemanticRefusal

    if release is None:
        return _compile_packs(
            ctx,
            domain or ["statistics"],
            domains,
            None,
            json_,
            action="schema.check",
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
    from corpus_structure.cli.diagnostic_artifacts import (
        diagnostic_scope,
        retain_optional_diagnostic,
    )
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
        validation_model = retain_optional_diagnostic(invocation, validation_model, context=failure)
        # A supplied success report always survives optional custody.
        assert validation_model is not None
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


@schema_app.command(
    "derive",
    epilog=(
        "Example: ci schema derive --domain statistics --out "
        "build/derived-model --json\n\nDomain contract: [domain "
        "reader](docs/design/D2-schema-and-guidelines.md)"
    ),
)
def derive_(
    out: Annotated[
        Path, typer.Option("--out", help="Artifact output directory.", rich_help_panel="Delivery")
    ],
    domain: Domain = None,
    domains: Domains = Path("domains"),
    json_: JsonOpt = False,
):
    """Export composed model artifacts; use native-candidate for native authoring."""
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.semantic.regeneration import prepare_packs

    with refusal(json_):
        if out.exists():
            raise SemanticRefusal("derivation requires a new --out directory")
        selected = domain or ["statistics"]
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
    acquired_revision: str | None = None
    native_base: NativeMigrationBase | None = None
    output: str
    native_operations: int
    ordinary_operations: int
    products: list[ArtifactRow]
    result_id: str | None = None
    acquired_target: StorageTarget | None = None
    selection: ConfiguredSelection | None = None
    operation_account: OperationAccount | None = None


def _render_native_candidate(result):
    table = Table("field", "value", title="native candidate")
    for key in ("database", "predecessor", "output", "native_operations", "ordinary_operations"):
        table.add_row(key, str(getattr(result, key)))
    table.add_row("current configuration", selection_summary(result.selection))
    table.add_row("acquired target", str(result.acquired_target or "unavailable"))
    return table


def _native_candidate_python(upgrade_ops, restore_sql: str) -> str:
    """Render operation-owned role custody without author-login restoration strings."""

    from alembic.autogenerate import render_python_code

    source = (
        "from alembic import op\nimport sqlalchemy as sa\n"
        "from sqlalchemy import Text\nfrom sqlalchemy.dialects import postgresql\n"
        "import pgvector.sqlalchemy\n"
        "from corpus_structure.semantic import alembic_native, alembic_privileges\n\n"
        "from corpus_structure.schema.relational import Vector\n\n"
        "def upgrade():\n" + render_python_code(upgrade_ops) + "\n"
    )
    return source


def author_native_candidate(
    settings,
    authoring_database: str | None,
    predecessor_state: Path | None,
    *,
    expected_predecessor: str | None = None,
    native_base: NativeMigrationBase | None = None,
    expected_target: StorageTarget | None = None,
    target_metadata: MetaData | None = None,
    retire: frozenset[NativeIdentity] = frozenset(),
    recreate: frozenset[NativeIdentity] = frozenset(),
    data_steps: tuple[Literal["pdf-visual-mapping", "characterization-source-scope"], ...] = (),
) -> tuple[NativeCandidateResult, dict[str, bytes]]:
    """Use the owned rollback-only authoring connection to prepare immutable product bytes."""
    from hashlib import sha256

    from sqlalchemy.engine import make_url

    from corpus_structure.semantic.alembic_native import NativeTransitionOp
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.migrations import current_revision, migration_fence
    from corpus_structure.semantic.native_candidate import (
        authored_admission_sql,
        prepare_series_candidate,
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
    if len(set(data_steps)) != len(data_steps):
        raise NativeAuthoringError("named data steps must be unique")
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
            if native_base is not None:
                from corpus_structure.semantic.migration_chain import frozen_base_location
                from corpus_structure.semantic.migrations import ALEMBIC_DIR, upgrade

                if (
                    predecessor != native_base.acquired_revision
                    or expected_predecessor != native_base.predecessor
                ):
                    raise SemanticRefusal("native authoring base differs from the preview")
                with frozen_base_location(ALEMBIC_DIR, native_base) as location:
                    upgrade(
                        conn,
                        native_base.predecessor,
                        expected_predecessor=predecessor,
                        script_location=location,
                    )
                predecessor = current_revision(conn)
                if predecessor != native_base.predecessor:
                    raise SemanticRefusal("native authoring chain did not reach its predecessor")
            if predecessor is None:
                raise SemanticRefusal("native authoring has no migrated predecessor")
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
            from corpus_structure.semantic.alembic_privileges import PrivilegeTransitionOp, OwnedSQLOp, operation_record
            from corpus_structure.semantic.native_data_steps import build_data_step
            for step in data_steps:
                statement = str(build_data_step(step, target_metadata).compile(dialect=conn.dialect, compile_kwargs={"literal_binds": True}))
                upgrade_ops.ops.append(OwnedSQLOp("corpus_sem_publisher", statement))
            native = [item for item in upgrade_ops.ops if isinstance(item, (NativeTransitionOp, PrivilegeTransitionOp))]
            migration_role = conn.exec_driver_sql("SELECT current_user").scalar_one()
            python_source = _native_candidate_python(
                upgrade_ops,
                "SET LOCAL ROLE " + conn.dialect.identifier_preparer.quote(migration_role),
            )
            compile(python_source, "native_candidate.py", "exec")
            # Reuse the admission already normalized with the candidate's new
            # physical row types in scope; rebuilding after its savepoint rolls
            # back cannot resolve those types and would author a second answer.
            admission = authored_admission_sql(authoring)
            products = {
                "native_candidate.py": python_source.encode(),
                "native_operations.json": canonical_bytes(
                    {
                        "version": 2,
                        "predecessor": predecessor,
                        "operations": [operation_record(item) for item in native],
                        "privileges": list(script.privilege_policies),
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
        acquired_revision=predecessor if native_base is None else native_base.acquired_revision,
        native_base=native_base,
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


@schema_app.command(
    "native-candidate",
    epilog=(
        "Example: ci schema native-candidate --out build/native-candidate "
        "--json\n\nDomain contract: [domain "
        "reader](docs/design/D2-schema-and-guidelines.md)"
    ),
)
def native_candidate_(
    ctx: typer.Context,
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Artifact output directory.", rich_help_panel="Delivery"),
    ] = None,
    authoring_database: Annotated[
        str | None,
        typer.Option(
            "--authoring-database",
            help="Rollback-only authoring database; defaults to the configured target.",
        ),
    ] = None,
    predecessor_state: Annotated[
        Path | None,
        typer.Option(
            "--predecessor-state",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Prior native state declaration JSON.",
            rich_help_panel="Inputs",
        ),
    ] = None,
    intent: Annotated[
        Path | None, typer.Option(help="YAML retirement and recreation declaration.")
    ] = None,
    observations: Annotated[
        bool,
        typer.Option(
            "--observations/--no-observations",
            help="Retain safe structured native-authoring observations.",
        ),
    ] = False,
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
        with store.operation("schema.native-candidate", observations=observations) as result:
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
            report = report.model_copy(update={"selection": current_selection(ctx, "development")})
            result.settle(predecessor=report.predecessor, target=report.database)
        if out is not None:
            out.parent.mkdir(parents=True, exist_ok=True)
            delivered = store.deliver(result.id, "candidate", out)
            report = report.model_copy(update={"output": str(delivered)})
        emit(report, json=json_, render=_render_native_candidate)


@schema_app.command(
    "explain-operation",
    epilog=(
        "Example: ci schema explain-operation OPERATION --release RELEASE "
        "--dependency-detail --json\n\nDomain contract: [domain "
        "reader](docs/design/D2-schema-and-guidelines.md)"
    ),
)
def explain_operation_(
    ctx: typer.Context,
    operation: Annotated[
        str, typer.Argument(metavar="OPERATION", help="Declared operation identifier.")
    ],
    release: Annotated[
        str,
        typer.Option("--release", help="Archived semantic release ID.", rich_help_panel="Inputs"),
    ],
    subject: Annotated[
        Path | None,
        typer.Option(
            "--subject",
            help="JSON file containing the operation subject.",
            rich_help_panel="Inputs",
        ),
    ] = None,
    dependency_detail: DependencyDetail = False,
    dependency_family: DependencyFamily = None,
    dependency_output: DependencyOutput = None,
    dependency_occurrence: DependencyOccurrence = None,
    dependency_after: DependencyAfter = 0,
    dependency_limit: DependencyLimit = 100,
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


@schema_app.command(
    "diff",
    epilog=(
        "Example: ci schema diff BEFORE_RELEASE AFTER_RELEASE "
        "--dependency-detail --json\n\nDomain contract: [domain "
        "reader](docs/design/D2-schema-and-guidelines.md)"
    ),
)
def diff_(
    ctx: typer.Context,
    before: Annotated[str, typer.Argument(metavar="BEFORE", help="Before semantic release ID.")],
    after: Annotated[str, typer.Argument(metavar="AFTER", help="After semantic release ID.")],
    source_run_id: Annotated[
        int | None,
        typer.Option(
            min=1,
            help="Pinned source run for interpretation-use comparison.",
            rich_help_panel="Inputs",
        ),
    ] = None,
    review_run_id: Annotated[
        int | None, typer.Option(min=1, help="Pinned private review run.", rich_help_panel="Inputs")
    ] = None,
    review_cut_id: Annotated[
        int | None, typer.Option(min=1, help="Pinned review cut.", rich_help_panel="Inputs")
    ] = None,
    use_limit: Annotated[
        int, typer.Option(min=1, max=1000, help="Maximum retained use entries.")
    ] = 100,
    use_after: Annotated[
        str | None,
        typer.Option(
            help="Opaque continuation for retained interpretation uses.", rich_help_panel="Inputs"
        ),
    ] = None,
    use_side: Literal["before", "after"] = "before",
    dependency_detail: DependencyDetail = False,
    dependency_family: DependencyFamily = None,
    dependency_output: DependencyOutput = None,
    dependency_occurrence: DependencyOccurrence = None,
    dependency_after: DependencyAfter = 0,
    dependency_limit: DependencyLimit = 100,
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


@schema_app.command(
    "inspect",
    epilog=(
        "Example: ci schema inspect --release RELEASE --subject-kind "
        "operation --subject OPERATION --view detail --json\n\nDomain "
        "contract: [domain reader](docs/design/D2-schema-and-guidelines.md"
        ")"
    ),
)
def inspect_contract_command(
    ctx: typer.Context,
    release: Annotated[
        str,
        typer.Option("--release", help="Archived semantic release ID.", rich_help_panel="Inputs"),
    ],
    subject_kind: ContractKindOption,
    subject: Annotated[
        str,
        typer.Option("--subject", help="Released subject identifier.", rich_help_panel="Inputs"),
    ],
    property_: Annotated[
        str | None,
        typer.Option(
            "--property",
            help="Released property identifier for property inspection.",
            rich_help_panel="Inputs",
        ),
    ] = None,
    view: ContractViewOption = "summary",
    after: Annotated[
        str | None,
        typer.Option(
            help="Opaque cursor returned by the selected contract page.", rich_help_panel="Inputs"
        ),
    ] = None,
    limit: ContractLimit = 20,
    input_: ContractInput = None,
    validation_purpose: ValidationPurposeOption = None,
    correction_detail: CorrectionDetail = False,
    raw_evidence: RawEvidence = False,
    max_errors: CorrectionErrors = 100,
    max_depth: CorrectionDepth = 8,
    max_bytes: CorrectionBytes = 262144,
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


@schema_app.command(
    "diagnostic",
    epilog=(
        "Example: ci schema diagnostic RESULT_ID --json\n\nDomain contract: "
        "[domain reader](docs/design/D2-schema-and-guidelines.md)"
    ),
)
def inspect_diagnostic_command(
    ctx: typer.Context,
    result_id: Annotated[
        str, typer.Argument(metavar="RESULT_ID", help="Managed diagnostic result ID.")
    ],
    raw_evidence: RawEvidence = False,
    max_bytes: DiagnosticBytes = 8 * 1024 * 1024,
    view: Annotated[
        Literal["summary", "correction", "document"] | None,
        typer.Option(help="Default: correction for human output; original document for JSON."),
    ] = None,
    max_errors: CorrectionErrors = 100,
    max_depth: CorrectionDepth = 8,
    projection_bytes: Annotated[
        int,
        typer.Option(
            min=1024,
            max=1048576,
            help="Selected summary/correction byte budget; separate from retained read bytes.",
        ),
    ] = 262144,
    source: Annotated[
        str | None,
        typer.Option(
            help="Exact retained source module; requires correction view and raw collection."
        ),
    ] = None,
    source_line: Annotated[
        int,
        typer.Option(
            min=1, help="Actual starting source line, never inferred from a logical path."
        ),
    ] = 1,
    source_lines: Annotated[int, typer.Option(min=1, max=100)] = 20,
    source_bytes: Annotated[int, typer.Option(min=1024, max=65536)] = 16384,
    json_: JsonOpt = False,
):
    """Read retained correction evidence under its original immutable binding."""
    import json

    from corpus_structure.cli.correction_rendering import render_correction
    from corpus_structure.cli.diagnostic_artifacts import read_diagnostic
    from corpus_structure.cli.managed import ResultError, result_boundary, result_store
    from corpus_structure.cli.output import stdout_console, write_report_text
    from corpus_structure.semantic.diagnostic_selection import select_diagnostic

    selected_view = view or ("document" if json_ else "correction")
    if source is not None and selected_view != "correction":
        raise typer.BadParameter("--source requires --view correction")
    with result_boundary(json_):
        store = result_store(ctx)
        with store.lease(result_id):
            document = read_diagnostic(
                store, result_id, raw_evidence=raw_evidence, max_bytes=max_bytes
            )
            manifest = store.show(result_id)
            try:
                selected = select_diagnostic(
                    document,
                    selected_view,
                    result_id=result_id,
                    invocation={
                        "id": result_id,
                        "action": manifest.action,
                        "outcome": manifest.outcome,
                    },
                    max_errors=max_errors,
                    max_depth=max_depth,
                    max_bytes=projection_bytes,
                    source=source,
                    raw_evidence=raw_evidence,
                    source_line=source_line,
                    source_lines=source_lines,
                    source_bytes=source_bytes,
                )
            except ValueError as error:
                raise ResultError(str(error)) from error
        if json_ or selected_view == "document":
            write_report_text(json.dumps(selected, indent=None if json_ else 2) + "\n")
        else:
            stdout_console().print(render_correction(selected))
