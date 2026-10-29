"""Reproducible source execution on the semantic deployment; explicit run resumption."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from corpus_structure.cli.output import JsonOpt, emit, state, stderr_console


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
    slice: Annotated[str, typer.Option(help="Named source scope.")] = "trace",
    resume_run: Annotated[int | None, typer.Option(help="Resume this existing run; never create replacement occurrences.")] = None,
    automated: Annotated[bool, typer.Option("--automated/--prepare-only")] = True,
    select_result: Annotated[bool, typer.Option("--select-result/--leave-unselected")] = True,
    json: JsonOpt = False,
) -> None:
    """Prepare, ingest, extract, consolidate and infer from actual source documents.

    Run `ci db init` first. This command never migrates or reads a legacy knowledge database.
    Reference grading is a separate `ci eval` operation with evaluator credentials.
    """
    from corpus_structure.intervene.automated import extract_run
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.orchestrate.commands import finalize_bound_run, start_bound_run
    from corpus_structure.orchestrate.project import init_bound_project
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.regeneration import prepare_pack
    from corpus_structure.semantic.releases import activation_token, activate_release, persist_release, load_release
    from corpus_structure.semantic.runtime import open_runtime_engine, select_completed_result

    settings = state(ctx).settings()
    project = project or settings.runtime.default_project
    from corpus_structure.semantic.types import PreparedRelease

    prepared: PreparedRelease | None = None
    source_id: str | None = None
    try:
        if Path(domain).name != domain:
            raise ValueError("domain must name a declared pack")
        if resume_run is None:
            bundle, deps, profile, prepared = prepare_pack(DOMAINS / domain)
            source_id = f"source:{project}:{prepared.release_id}"
            # Preparation and source registration do not change the selected answer snapshot.
            with open_runtime_engine(settings, "ci-regenerate-prepare", purpose="maintenance") as engine:
                with engine.begin() as conn:
                    persist_release(conn, bundle, deps, profile, prepared)
        with open_runtime_engine(settings, "ci-regenerate") as engine:
            if resume_run is None:
                assert prepared is not None and source_id is not None
                with engine.begin() as conn:
                    init_bound_project(conn, domain=domain, corpus=corpus.resolve(), name=project,
                                       release_id=prepared.release_id, realization_id=source_id)
                run = start_bound_run(engine, release_id=prepared.release_id, realization_id=source_id,
                                      project_id=project, domain=domain,
                                      method_settings=MethodSettings(data_dir=settings.paths.data_dir,
                                                                     model_cache=settings.paths.model_cache), slice=slice)
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
                emit(RegenerationReport(project=project, release_id=prepared.release_id,
                     source_realization_id=source_id, run_id=run_id, status="prepared"), json=json)
                return
            runs = table("ops.run")
            with engine.connect() as conn:
                completed = conn.execute(select(runs.c.result_realization_id).where(runs.c.id == run_id)).scalar_one()
            extracted = None if completed else extract_run(engine, settings, run_id)
            provider = None if extracted is None else extracted.model_dump(mode="json")
            output = completed or f"result:{project}:{run_id}"
            finalize_bound_run(engine, run_id, output)
        generation = None
        if select_result:
            # Both pointer changes share one transaction and generation fence, after complete output.
            with open_runtime_engine(settings, "ci-regenerate-select", purpose="maintenance") as engine:
                with engine.begin() as conn:
                    projects = table("data.project")
                    selected = conn.execute(select(projects).where(projects.c.project_id == project)
                                            .with_for_update()).mappings().one()
                    token = activation_token(conn, project)
                    if selected["selected_result_run_id"] == run_id:
                        generation = token.generation
                    else:
                        if resume_run is None or token.release_id is None:
                            token = activate_release(conn, project, prepared.release_id,
                                                     expected_parent=token.release_id, expected_generation=token.generation)
                        generation = select_completed_result(conn, project, run_id, token.generation)
        emit(RegenerationReport(project=project, release_id=prepared.release_id,
             source_realization_id=source_id, run_id=run_id, status="complete", output_realization_id=output,
             selected_generation=generation, provider=provider), json=json)
    except (ValueError, KeyError) as error:
        stderr_console().print(f"refused: {error}")
        raise typer.Exit(code=1) from None


def register(app: typer.Typer) -> None:
    app.command("regenerate")(regenerate)
