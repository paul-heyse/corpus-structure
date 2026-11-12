"""Reproducible source execution on the semantic deployment; explicit run resumption."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import BaseModel, ConfigDict, Field, JsonValue, RootModel
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from corpus_structure.cli.characterization_options import (
    method_settings as resolved_method_settings,
)
from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, diagnostic, emit, state, stderr_console
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.refusals import SemanticRefusal


class RegenerationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    invocation_id: str | None = None
    project: str
    release_id: str
    source_realization_id: str
    run_id: int
    status: str
    readiness: str
    output_realization_id: str | None = None
    selected_generation: int | None = None
    provider: dict[str, object] | None = None
    semantic_impact: dict | None = None
    compatibility_advice: tuple[str, ...] = ()
    characterization_views: tuple[ProductReference, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )


def read_product_pin(path: Path | None, role: str) -> ProductReference | None:
    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context

    if path is None:
        return None
    try:
        pin = (
            trusted_pdf_context()
            .boundary.validate_json("PdfProductReference", path.read_bytes())
            .model_dump(mode="python")
        )
        return ProductReference(**pin)
    except (ValueError, OSError) as error:
        raise SemanticRefusal(f"invalid {role} source product pin: {error}") from error


def regenerate(
    ctx: typer.Context,
    domain: Annotated[
        str | None, typer.Option(help="Executable domain pack for a new run.")
    ] = None,
    corpus: Annotated[Path | None, typer.Option(exists=True, file_okay=False)] = None,
    project: Annotated[str | None, typer.Option()] = None,
    slice: Annotated[
        str | None,
        typer.Option(help="Named source scope (uses the pack's declared default scope)."),
    ] = None,
    scope: Annotated[str | None, typer.Option(help="Named source scope.")] = None,
    whole_document: Annotated[
        bool, typer.Option(help="Explicitly select all native document content.")
    ] = False,
    source_membership: Annotated[
        Literal["direct", "descendants"] | None,
        typer.Option(help="Exact native section membership."),
    ] = None,
    native_source: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Exact retained native product pin JSON; reuse conversion as this run's input.",
        ),
    ] = None,
    integrated_source: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Exact retained integrated product pin JSON; reuse selected content as input.",
        ),
    ] = None,
    resume_run: Annotated[
        int | None,
        typer.Option(help="Resume this existing run; never create replacement occurrences."),
    ] = None,
    automated: Annotated[bool, typer.Option("--automated/--prepare-only")] = True,
    select_result: Annotated[bool, typer.Option("--select-result/--leave-unselected")] = False,
    activate: Annotated[
        bool, typer.Option("--activate-release", help="Explicitly activate the run's release.")
    ] = False,
    json: JsonOpt = False,
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
) -> None:
    """Prepare, ingest, extract, consolidate and infer from actual source documents.

    Run `ci db init` first. This command never migrates or reads a legacy knowledge database.
    Reference grading is a separate `ci eval` operation with evaluator credentials.
    """
    from corpus_structure.intervene.automated import extract_run
    from corpus_structure.orchestrate.commands import (
        finalize_bound_run,
        run_readiness,
        run_source_ready,
        start_bound_run,
    )
    from corpus_structure.orchestrate.liveness import supervise_run
    from corpus_structure.orchestrate.project import init_bound_project
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.authored_sql import (
        AuthoredSQL,
        admit_archived_sql,
        analyze_archived_sql,
        has_authored_sql,
    )
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.regeneration import prepare_pack
    from corpus_structure.semantic.releases import (
        ActivationToken,
        activate_release,
        load_release,
        persist_release,
    )
    from corpus_structure.semantic.runtime import open_runtime_engine, select_completed_result
    from corpus_structure.semantic.types import PreparedRelease

    def sql_products(release_id: str) -> dict[str, AuthoredSQL]:
        with (
            open_runtime_engine(settings, "ci-regenerate-sql", purpose="read") as sql_engine,
            sql_engine.connect() as sql_conn,
        ):
            return analyze_archived_sql(sql_conn, release_id)

    if whole_document and (slice is not None or scope is not None):
        raise typer.BadParameter("whole-document is mutually exclusive with slice and scope")
    if resume_run is not None and (
        whole_document or source_membership is not None or slice is not None or scope is not None
    ):
        raise typer.BadParameter("a resumed run retains its original source selection")
    prepared: PreparedRelease | None = None
    source_id: str | None = None
    impact, advice = None, ()
    from corpus_structure.cli.managed import result_store
    from corpus_structure.cli.observation_logging import bound
    from corpus_structure.orchestrate.commands import CommandError
    from corpus_structure.orchestrate.project import ProjectError
    from corpus_structure.semantic.authored_sql import SQLAdmissionError
    from corpus_structure.semantic.domain_operations import DomainOperationRefused
    from corpus_structure.semantic.execution_admission import ExecutionAdmissionError
    from corpus_structure.semantic.publication import PublicationConflict
    from corpus_structure.semantic.releases import ActivationConflict, ReleaseConflict

    with (
        result_store(ctx).operation(
            "run.resume" if resume_run is not None else "regenerate",
            scope={"resume_run": resume_run},
            observations=True,
        ) as invocation,
        failure_boundary(
            json,
            expected=(
                CommandError,
                ProjectError,
                OperationConflict,
                SQLAdmissionError,
                DomainOperationRefused,
                ExecutionAdmissionError,
                PublicationConflict,
                ActivationConflict,
                ReleaseConflict,
            ),
        ) as failure,
    ):
        settings = state(ctx).settings()
        method_settings = resolved_method_settings(settings, execution_policy)
        project = project or settings.runtime.default_project
        if not automated and (select_result or activate):
            raise SemanticRefusal("source preparation cannot select a result or activate a release")
        if native_source is not None and integrated_source is not None:
            raise SemanticRefusal("native-source and integrated-source are mutually exclusive")
        if resume_run is not None and (native_source is not None or integrated_source is not None):
            raise SemanticRefusal("a resumed run retains its original source input binding")
        native_product = read_product_pin(native_source, "native")
        integrated_product = read_product_pin(integrated_source, "integrated")
        completed = None
        readiness = "source_ready"
        run_state = "running"
        if resume_run is None:
            if domain is None or corpus is None:
                raise SemanticRefusal("a new run requires --domain and --corpus")
            if Path(domain).name != domain:
                raise SemanticRefusal("domain must name a declared pack")
            bundle, deps, profile, prepared = prepare_pack(DOMAINS / domain)
            failure.bind(prepared, "regenerate")
            source_id = f"source:{project}:{prepared.release_id}"
            # Preparation and source registration do not change the selected answer snapshot.
            with (
                open_runtime_engine(settings, "ci-regenerate-prepare", purpose="admit") as engine,
                engine.begin() as conn,
            ):
                persist_release(conn, bundle, deps, profile, prepared)
                if not has_authored_sql(prepared):
                    admit_release(prepared, connection=conn)
            if has_authored_sql(prepared):
                analyzed = sql_products(prepared.release_id)
                with (
                    open_runtime_engine(
                        settings, "ci-regenerate-admit", purpose="admit"
                    ) as admission_engine,
                    admission_engine.begin() as admission_conn,
                ):
                    admit_archived_sql(admission_conn, prepared.release_id, analyzed=analyzed)
                    admit_release(prepared, connection=admission_conn)
        purpose = "read" if resume_run is not None and not automated else "write"
        with open_runtime_engine(settings, "ci-regenerate", purpose=purpose) as engine:
            from corpus_structure.semantic.storage_target import acquired_target

            try:
                with engine.connect() as target_connection:
                    target = acquired_target(target_connection, purpose=purpose)
                invocation.manifest.details["observation_target"] = target.model_dump(mode="json")
            except Exception as binding_error:
                invocation.observe(
                    "binding_unavailable",
                    "Native inspection storage binding unavailable",
                    reason=type(binding_error).__name__,
                )
            invocation.stage("native_run", project=project)
            if resume_run is not None:
                from corpus_structure.semantic.visual_requests import (
                    acquire_visual_resume,
                    execute_visual_resume,
                )

                visual_resume = acquire_visual_resume(
                    engine,
                    resume_run,
                    project=project,
                    prepare_only=not automated,
                    select_result=select_result,
                    activate_release=activate,
                )
                if visual_resume is not None:
                    invocation.bind_observations(
                        run_id=visual_resume.run_id,
                        project=visual_resume.project,
                        release_id=visual_resume.release_id,
                    )
                    invocation.stage("visual_resume")
                    with bound(
                        run_id=visual_resume.run_id,
                        project=visual_resume.project,
                        release_id=visual_resume.release_id,
                    ):
                        visual = execute_visual_resume(
                            visual_resume,
                            receipts=settings.nemotron.receipts,
                            nemotron_endpoint=settings.nemotron.endpoint,
                        )
                    invocation.observe(
                        "native_visual_resume",
                        "Native visual resume returned",
                        run_id=resume_run,
                        status=visual.status,
                    )
                    failed = visual.status == "failed"
                    # CLI custody is a projection over the native result, never a native field.
                    observed = RootModel[dict[str, JsonValue]](
                        {**visual.model_dump(mode="json"), "invocation_id": invocation.id}
                    )
                    emit(observed, json=json, exit_code=int(failed))
                    if failed:
                        raise typer.Exit(1)
                    return
            if resume_run is None:
                assert prepared is not None and source_id is not None
                assert domain is not None and corpus is not None
                with engine.begin() as conn:
                    init_bound_project(
                        conn,
                        domain=domain,
                        corpus=corpus.resolve(),
                        name=project,
                        release_id=prepared.release_id,
                        realization_id=source_id,
                        native_product=native_product,
                        integrated_product=integrated_product,
                    )
                from corpus_structure.orchestrate.semantic import SourceRunCreated

                def source_created(created: SourceRunCreated) -> None:
                    from corpus_structure.orchestrate.characterization_recovery import (
                        record_characterization_run,
                    )

                    if record_characterization_run(invocation, engine, created):
                        return
                    bindings = {
                        "run_id": created.run_id,
                        "project": created.project,
                        "release_id": created.release_id,
                    }
                    try:
                        invocation.bind_observations(**bindings)
                        invocation.stage("source_running", run_id=created.run_id)
                    except Exception as binding_error:
                        # Optional diagnostics cannot replace native source work or its failure.
                        reason = type(binding_error).__name__
                        invocation.manifest.details["observation_binding_unavailable"] = reason
                        try:
                            invocation.observe(
                                "binding_unavailable",
                                "Native run observation binding unavailable",
                                reason=reason,
                            )
                            diagnostic("Native run observation binding unavailable: " + reason)
                        except Exception:
                            pass

                run = start_bound_run(
                    engine,
                    on_created=source_created,
                    release_id=prepared.release_id,
                    realization_id=source_id,
                    project_id=project,
                    domain=domain,
                    method_settings=method_settings,
                    slice=slice,
                    scope=scope,
                    whole_document=whole_document,
                    source_membership=source_membership,
                    native_product=native_product,
                    integrated_product=integrated_product,
                )
                run_id = run.run_id
            else:
                run_id = resume_run
                runs = table("ops.run")
                with engine.connect() as conn:
                    try:
                        row = conn.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
                    except NoResultFound as error:
                        raise OperationConflict(f"no semantic run {run_id}") from error
                    if row["project_id"] != project:
                        raise OperationConflict("resume run has another project")
                    completed = row["result_realization_id"]
                    run_state = row["status"]
                    readiness = run_readiness(run_state, completed, run_source_ready(conn, run_id))
                    if readiness == "terminal":
                        raise OperationConflict(f"run {run_id} is terminal ({run_state})")
                    if readiness == "incomplete":
                        raise OperationConflict(
                            f"run {run_id} has no retained source-ready cut; inspect status "
                            "before cancelling or starting a replacement"
                        )
                    prepared = load_release(conn, row["release_id"])
                    failure.bind(prepared, "regenerate")
                    source_id = row["input_realization_id"]
            assert prepared is not None and source_id is not None
            if resume_run is not None:
                invocation.bind_observations(
                    run_id=run_id, project=project, release_id=prepared.release_id
                )
            invocation.stage("source_ready", run_id=run_id)
            # Report meaning changes from the retained selected release even when
            # the caller leaves the new result unselected. This grants no admission.
            with engine.connect() as conn:
                runs = table("ops.run")
                source_options = conn.scalar(select(runs.c.options).where(runs.c.id == run_id))
                characterization_views = tuple(
                    ProductReference(**pin)
                    for pin in (source_options or {}).get("characterization_views", ())
                )
                projects = table("data.project")
                before_release = conn.scalar(
                    select(projects.c.active_release_id).where(projects.c.project_id == project)
                )
                if before_release is not None:
                    from corpus_structure.semantic.operation_reporting import (
                        compare_semantic_releases,
                        compatibility_advice,
                    )

                    compared = compare_semantic_releases(
                        load_release(conn, before_release), prepared
                    )
                    impact = compared.model_dump(mode="json")
                    advice = compatibility_advice(compared)
            stderr_console().print(f"semantic run {run_id}; resume with ci run resume {run_id}")
            if not automated:
                emit(
                    RegenerationReport(
                        invocation_id=invocation.id,
                        project=project,
                        release_id=prepared.release_id,
                        source_realization_id=source_id,
                        run_id=run_id,
                        status="complete" if completed else "prepared",
                        readiness=readiness,
                        output_realization_id=completed,
                        semantic_impact=impact,
                        compatibility_advice=advice,
                        characterization_views=characterization_views,
                    ),
                    json=json,
                )
                return
            provider = None
            if completed is None and run_state != "consolidating":
                invocation.stage("provider", run_id=run_id)
                with (
                    bound(run_id=run_id, project=project, release_id=prepared.release_id),
                    supervise_run(engine, run_id),
                ):
                    extracted = extract_run(engine, settings, run_id)
                    provider = extracted.model_dump(mode="json") if extracted is not None else None
            output = completed or f"result:{project}:{run_id}"
            if completed is None:
                invocation.stage("finalizing", run_id=run_id)
                finalize_bound_run(engine, run_id, output, analytics=settings.analytics)
        generation = None
        if activate or select_result:
            assert prepared is not None
            analyzed = sql_products(prepared.release_id) if has_authored_sql(prepared) else {}
            # Both pointer changes share one transaction and generation fence.
            with (
                open_runtime_engine(settings, "ci-regenerate-select", purpose="admit") as engine,
                engine.begin() as conn,
            ):
                projects = table("data.project")
                selected = (
                    conn.execute(select(projects).where(projects.c.project_id == project))
                    .mappings()
                    .one()
                )
                token = ActivationToken(selected["active_release_id"], selected["generation"])
                if token.release_id != prepared.release_id:
                    if not activate:
                        raise OperationConflict(
                            "selecting this run requires explicit --activate-release"
                        )
                    token = activate_release(
                        conn,
                        project,
                        prepared.release_id,
                        expected_parent=token.release_id,
                        expected_generation=token.generation,
                        sql_admissions=analyzed,
                    )
                if select_result:
                    if selected["selected_result_run_id"] == run_id:
                        generation = token.generation
                    else:
                        generation = select_completed_result(
                            conn, project, run_id, token.generation
                        )
        emit(
            RegenerationReport(
                invocation_id=invocation.id,
                project=project,
                release_id=prepared.release_id,
                source_realization_id=source_id,
                run_id=run_id,
                status="complete",
                readiness="completed",
                output_realization_id=output,
                selected_generation=generation,
                provider=provider,
                semantic_impact=impact,
                compatibility_advice=advice,
                characterization_views=characterization_views,
            ),
            json=json,
        )


def register(app: typer.Typer) -> None:
    app.command("regenerate")(regenerate)
