"""Reproducible source execution on the semantic deployment; explicit run resumption."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, emit, state, stderr_console
from corpus_structure.semantic.refusals import SemanticRefusal


class RegenerationReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    project: str
    release_id: str
    source_realization_id: str
    run_id: int
    status: str
    output_realization_id: str | None = None
    selected_generation: int | None = None
    provider: dict[str, object] | None = None


def regenerate(
    ctx: typer.Context,
    domain: Annotated[str, typer.Option(help="Explicit executable domain pack.")],
    corpus: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    project: Annotated[str | None, typer.Option()] = None,
    slice: Annotated[
        str | None,
        typer.Option(help="Named source scope (uses the pack's declared default scope)."),
    ] = None,
    scope: Annotated[str | None, typer.Option(help="Named source scope.")] = None,
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
    select_result: Annotated[bool, typer.Option("--select-result/--leave-unselected")] = True,
    json: JsonOpt = False,
) -> None:
    """Prepare, ingest, extract, consolidate and infer from actual source documents.

    Run `ci db init` first. This command never migrates or reads a legacy knowledge database.
    Reference grading is a separate `ci eval` operation with evaluator credentials.
    """
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.intervene.automated import extract_run
    from corpus_structure.orchestrate.commands import finalize_bound_run, start_bound_run
    from corpus_structure.orchestrate.project import init_bound_project
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.regeneration import prepare_pack
    from corpus_structure.semantic.releases import (
        ActivationToken,
        activate_release,
        load_release,
        persist_release,
    )
    from corpus_structure.semantic.runtime import open_runtime_engine, select_completed_result

    settings = state(ctx).settings()
    project = project or settings.runtime.default_project
    from corpus_structure.semantic.authored_sql import (
        AuthoredSQL,
        admit_archived_sql,
        analyze_archived_sql,
        has_authored_sql,
    )
    from corpus_structure.semantic.publication import admit_release
    from corpus_structure.semantic.types import PreparedRelease

    def sql_products(release_id: str) -> dict[str, AuthoredSQL]:
        with (
            open_runtime_engine(settings, "ci-regenerate-sql", purpose="read") as sql_engine,
            sql_engine.connect() as sql_conn,
        ):
            return analyze_archived_sql(sql_conn, release_id)

    prepared: PreparedRelease | None = None
    source_id: str | None = None
    from corpus_structure.orchestrate.commands import CommandError
    from corpus_structure.orchestrate.project import ProjectError
    from corpus_structure.semantic.authored_sql import SQLAdmissionError
    from corpus_structure.semantic.domain_operations import DomainOperationRefused
    from corpus_structure.semantic.execution_admission import ExecutionAdmissionError
    from corpus_structure.semantic.publication import PublicationConflict
    from corpus_structure.semantic.releases import ActivationConflict, ReleaseConflict

    with failure_boundary(
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
    ):
        if Path(domain).name != domain:
            raise SemanticRefusal("domain must name a declared pack")
        if native_source is not None and integrated_source is not None:
            raise SemanticRefusal("native-source and integrated-source are mutually exclusive")
        if resume_run is not None and (native_source is not None or integrated_source is not None):
            raise SemanticRefusal("a resumed run retains its original source input binding")
        from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
        from corpus_structure.semantic.product_reference import ProductReference

        def product_pin(path: Path | None, role: str) -> ProductReference | None:
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

        native_product = product_pin(native_source, "native")
        integrated_product = product_pin(integrated_source, "integrated")
        if resume_run is None:
            bundle, deps, profile, prepared = prepare_pack(DOMAINS / domain)
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
        with open_runtime_engine(settings, "ci-regenerate", purpose="write") as engine:
            if resume_run is None:
                assert prepared is not None and source_id is not None
                with engine.begin() as conn:
                    init_bound_project(
                        conn,
                        domain=domain,
                        corpus=corpus.resolve(),
                        name=project,
                        release_id=prepared.release_id,
                        realization_id=source_id,
                    )
                run = start_bound_run(
                    engine,
                    release_id=prepared.release_id,
                    realization_id=source_id,
                    project_id=project,
                    domain=domain,
                    method_settings=MethodSettings(
                        data_dir=settings.paths.data_dir,
                        model_cache=settings.paths.model_cache,
                        nemotron_endpoint=settings.nemotron.endpoint,
                        nemotron_python=settings.nemotron.python,
                        nemotron_worker=settings.nemotron.worker,
                        nemotron_receipts=settings.nemotron.receipts,
                        nemotron_timeout_seconds=settings.nemotron.timeout_seconds,
                    ),
                    slice=slice,
                    scope=scope,
                    native_product=native_product,
                    integrated_product=integrated_product,
                )
                run_id = run.run_id
            else:
                run_id = resume_run
                runs = table("ops.run")
                with engine.connect() as conn:
                    row = conn.execute(select(runs).where(runs.c.id == run_id)).mappings().one()
                    if row["project_id"] != project:
                        raise OperationConflict("resume run has another project")
                    prepared = load_release(conn, row["release_id"])
                    source_id = row["input_realization_id"]
            assert prepared is not None and source_id is not None
            stderr_console().print(f"semantic run {run_id}; resume with --resume-run {run_id}")
            if not automated:
                emit(
                    RegenerationReport(
                        project=project,
                        release_id=prepared.release_id,
                        source_realization_id=source_id,
                        run_id=run_id,
                        status="prepared",
                    ),
                    json=json,
                )
                return
            runs = table("ops.run")
            with engine.connect() as conn:
                completed = conn.execute(
                    select(runs.c.result_realization_id).where(runs.c.id == run_id)
                ).scalar_one()
            extracted = None if completed else extract_run(engine, settings, run_id)
            provider = None if extracted is None else extracted.model_dump(mode="json")
            output = completed or f"result:{project}:{run_id}"
            finalize_bound_run(engine, run_id, output, analytics=settings.analytics)
        generation = None
        if select_result:
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
                    token = activate_release(
                        conn,
                        project,
                        prepared.release_id,
                        expected_parent=token.release_id,
                        expected_generation=token.generation,
                        sql_admissions=analyzed,
                    )
                if selected["selected_result_run_id"] == run_id:
                    generation = token.generation
                else:
                    generation = select_completed_result(conn, project, run_id, token.generation)
        emit(
            RegenerationReport(
                project=project,
                release_id=prepared.release_id,
                source_realization_id=source_id,
                run_id=run_id,
                status="complete",
                output_realization_id=output,
                selected_generation=generation,
                provider=provider,
            ),
            json=json,
        )


def register(app: typer.Typer) -> None:
    app.command("regenerate")(regenerate)
