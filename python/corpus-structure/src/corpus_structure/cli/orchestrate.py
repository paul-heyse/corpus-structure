"""`ci project init`, `ci run` (with `ci run cancel`) and `ci tasks` (orchestration §3.13, P0-O-1).

`run` is a group whose callback starts a run when no subcommand is given (`invoke_without_command`
with `ctx.invoked_subcommand`). Its flags are the explicit options of §3.4's precedence; the result
prints every option as resolved, with its source. The work is in `orchestrate/commands.py`; a
refused command exits with code 1 and its reason on stderr. `ENGINE` and `PHASE0` are the seams
tests replace: the store opener and the graph with its pass and evaluation.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from json import loads
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from pydantic import BaseModel
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.output import JsonOpt, emit, state
from corpus_structure.core.vocab import AgentMode, AgentReuse, GpuMode, TaskStatus

project_app = typer.Typer(help="Create the project from a pack and corpus.", no_args_is_help=True)
run_app = typer.Typer(help="Start or cancel a run.", invoke_without_command=True)


@contextmanager
def _open_engine(settings: Any, timeout: float = 30.0) -> Generator[Any]:
    from corpus_structure.semantic.runtime import open_runtime_engine

    with open_runtime_engine(settings, timeout=timeout, purpose="write") as engine:
        yield engine


ENGINE: Callable[..., Any] = _open_engine


@contextmanager
def _open_read_engine(settings: Any, timeout: float = 5.0) -> Generator[Any]:
    from corpus_structure.semantic.runtime import open_runtime_engine

    with open_runtime_engine(settings, timeout=timeout, purpose="read") as engine:
        yield engine


READ_ENGINE: Callable[..., Any] = _open_read_engine


def _phase0() -> dict[str, Any]:
    from corpus_structure.orchestrate import phase0
    from corpus_structure.schema.pack import DOMAINS

    return {
        "registry_for": phase0.registry,
        "graph": phase0.PHASE0,
        "domains": DOMAINS,
    }


PHASE0: Callable[[], dict[str, Any]] = _phase0


def _refusals(json: bool):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.orchestrate import commands, project, registry
    from corpus_structure.orchestrate.errors import RunError
    from corpus_structure.orchestrate.policy import PolicyError
    from corpus_structure.orchestrate.slices import SliceError
    from corpus_structure.semantic.domain_operations import DomainOperationRefused
    from corpus_structure.semantic.operations import OperationConflict

    return failure_boundary(
        json,
        expected=(
            commands.CommandError,
            project.ProjectError,
            registry.RegistryError,
            RunError,
            OperationConflict,
            DomainOperationRefused,
            SliceError,
            PolicyError,
        ),
    )


def _table(title: str, result: BaseModel) -> Table:
    table = Table("field", "value", title=title)
    for name, value in result.model_dump(mode="json").items():
        table.add_row(name, str(value))
    return table


# --- ci project init --------------------------------------------------------------------------


@project_app.command("init")
def project_init(
    ctx: typer.Context,
    domain: Annotated[str, typer.Option(help="The pack under domains/.")],
    corpus: Annotated[Path, typer.Option(help="The corpus directory.", exists=True)],
    name: Annotated[
        str | None, typer.Option(help="The project name (default: the domain).")
    ] = None,
    semantic_release: Annotated[
        str | None, typer.Option(help="An already admitted semantic release.")
    ] = None,
    realization: Annotated[
        str | None, typer.Option(help="Explicit empty semantic realization identity.")
    ] = None,
    native_source: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    integrated_source: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    json: JsonOpt = False,
) -> None:
    """Create or update the project: its documents and the pack's versions."""
    from corpus_structure.cli.regenerate import read_product_pin
    from corpus_structure.orchestrate import project

    if native_source is not None and integrated_source is not None:
        raise typer.BadParameter("native-source and integrated-source are mutually exclusive")
    settings = state(ctx).settings()
    seams = PHASE0()
    with _refusals(json), ENGINE(settings) as engine, engine.begin() as conn:
        native_product = read_product_pin(native_source, "native")
        integrated_product = read_product_pin(integrated_source, "integrated")
        if semantic_release is None or realization is None:
            raise typer.BadParameter("initialization requires --semantic-release and --realization")
        report = project.init_bound_project(
            conn,
            domain=domain,
            corpus=corpus,
            release_id=semantic_release,
            realization_id=realization,
            name=name or settings.runtime.default_project,
            domains=seams["domains"],
            registry=seams["registry_for"](seams["domains"] / domain),
            native_product=native_product,
            integrated_product=integrated_product,
        )
    emit(report, json=json, render=lambda r: _table("project", r))


# --- ci run, ci run cancel --------------------------------------------------------------------


@run_app.callback()
def run(
    ctx: typer.Context,
    project: Annotated[
        str | None, typer.Option(help="The project (default: the only one).")
    ] = None,
    phase: Annotated[int, typer.Option(help="The run's phase.")] = 0,
    slice: Annotated[str | None, typer.Option(help="Run a named slice.")] = None,
    scope: Annotated[str | None, typer.Option(help="Propose within a named scope.")] = None,
    whole_document: Annotated[
        bool, typer.Option(help="Explicitly select the whole document, bypassing default scopes.")
    ] = False,
    source_membership: Annotated[
        Literal["direct", "descendants"] | None,
        typer.Option(help="Exact native section membership."),
    ] = None,
    corpus: Annotated[str | None, typer.Option(help="Ingest a named corpus slice.")] = None,
    agent_mode: Annotated[
        Literal["complete"] | None,
        typer.Option(help="complete (return after source preparation)."),
    ] = None,
    agent_reuse: Annotated[
        Literal["full"] | None, typer.Option(help="full (complete immutable packet reuse).")
    ] = None,
    gpu_mode: Annotated[GpuMode | None, typer.Option(help="The GPU mode.")] = None,
    fresh: Annotated[list[str] | None, typer.Option(help="A method not to reuse.")] = None,
    semantic_release: Annotated[
        str | None, typer.Option(help="Explicit admitted semantic release for source execution.")
    ] = None,
    realization: Annotated[
        str | None, typer.Option(help="Explicit semantic input realization.")
    ] = None,
    domain: Annotated[
        str, typer.Option(help="Method pack for explicit semantic source execution.")
    ] = "statistics",
    extraction_policy: Annotated[
        str, typer.Option(help="Explicit source policy: phase0 or m1-candidate.")
    ] = "phase0",
    m1_configuration: Annotated[
        str,
        typer.Option(
            help="M1 policy: source-only freezing or "
            "default/described/readings/contextual CPU extraction."
        ),
    ] = "default",
    record_policy: Annotated[
        Path | None,
        typer.Option(
            help="Finite fitted policy JSON for an M1 reading-resolution configuration.",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
    characterization_view: Annotated[
        list[str] | None,
        typer.Option(
            help="Exact enriched-document pin as a JSON object; repeat for multiple documents.",
        ),
    ] = None,
    integrated_product_task: Annotated[
        int | None, typer.Option(help="Exact retained integrated producing task.")
    ] = None,
    integrated_product_key: Annotated[
        str | None, typer.Option(help="Exact retained integrated product key.")
    ] = None,
    integrated_product_digest: Annotated[
        str | None, typer.Option(help="Exact retained integrated SHA-256 digest.")
    ] = None,
    json: JsonOpt = False,
) -> None:
    """Start a run over the project's corpus and run it to its end."""
    if ctx.invoked_subcommand is not None:
        return
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.orchestrate import commands

    if whole_document and (slice is not None or scope is not None):
        raise typer.BadParameter("whole-document is mutually exclusive with slice and scope")
    settings = state(ctx).settings()
    from corpus_structure.semantic.product_reference import ProductReference

    product_fields = (integrated_product_task, integrated_product_key, integrated_product_digest)
    if any(value is not None for value in product_fields) and not all(
        value is not None for value in product_fields
    ):
        raise typer.BadParameter(
            "integrated product task, key and digest must be supplied together"
        )
    if extraction_policy not in {"phase0", "m1-candidate"}:
        raise typer.BadParameter("unknown extraction policy")
    if m1_configuration not in {"default", "described", "readings", "contextual", "source-only"}:
        raise typer.BadParameter(
            "M1 configuration must be default, described, readings, contextual or source-only"
        )
    if extraction_policy == "phase0" and m1_configuration != "default":
        raise typer.BadParameter("nondefault M1 configuration requires the m1-candidate policy")
    if extraction_policy == "m1-candidate" and integrated_product_task is None:
        raise typer.BadParameter("M1 requires an exact retained integrated product pin")
    try:
        integrated_product = (
            ProductReference(
                integrated_product_task, integrated_product_key, integrated_product_digest
            )
            if integrated_product_task is not None
            and integrated_product_key is not None
            and integrated_product_digest is not None
            else None
        )
    except (TypeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    from corpus_structure.semantic.runtime import resolve_source_binding

    method_settings = MethodSettings(
        data_dir=settings.paths.data_dir,
        model_cache=settings.paths.model_cache,
        nemotron_endpoint=settings.nemotron.endpoint,
        nemotron_python=settings.nemotron.python,
        nemotron_worker=settings.nemotron.worker,
        nemotron_receipts=settings.nemotron.receipts,
        nemotron_timeout_seconds=settings.nemotron.timeout_seconds,
    )
    if gpu_mode is not None:
        raise typer.BadParameter("the selected semantic graph has no GPU operation")
    project = project or settings.runtime.default_project
    with _refusals(json), ENGINE(settings) as engine:
        with engine.connect() as conn:
            release_id, realization_id = resolve_source_binding(
                conn, project, release_id=semantic_release, realization_id=realization
            )
        report = commands.start_bound_run(
            engine,
            release_id=release_id,
            realization_id=realization_id,
            project_id=project,
            domain=domain,
            method_settings=method_settings,
            phase=phase,
            fresh=tuple(fresh or ()),
            slice=slice,
            scope=scope,
            whole_document=whole_document,
            source_membership=source_membership,
            corpus=corpus,
            agent_mode=str(agent_mode or AgentMode.COMPLETE),
            agent_reuse=str(agent_reuse or AgentReuse.FULL),
            extraction_policy=extraction_policy,
            m1_configuration=m1_configuration,
            record_policy=__import__("json").loads(record_policy.read_text())
            if record_policy
            else None,
            integrated_product=integrated_product,
            characterization_views=tuple(
                ProductReference(**loads(value)) for value in characterization_view or ()
            ),
            **{
                k: v
                for k, v in PHASE0().items()
                if k
                in (
                    {"domains"}
                    if extraction_policy == "m1-candidate"
                    else {"registry_for", "graph", "domains"}
                )
            },
        )
    emit(report, json=json)


@run_app.command("cancel")
def run_cancel(
    ctx: typer.Context,
    run_id: Annotated[int, typer.Argument(metavar="RUN")],
    semantic: Annotated[bool, typer.Option(hidden=True)] = False,
    json: JsonOpt = False,
) -> None:
    """Cancel a run and its open tasks."""
    from corpus_structure.orchestrate import commands

    with _refusals(json), ENGINE(state(ctx).settings()) as engine:
        report = commands.cancel_bound_run(engine, run_id)
    emit(report, json=json, render=lambda r: _table("cancelled", r))


@run_app.command("resume")
def run_resume(
    ctx: typer.Context,
    run_id: Annotated[int, typer.Argument(metavar="RUN")],
    project: Annotated[str | None, typer.Option(help="Project owning the retained run.")] = None,
    automated: Annotated[bool, typer.Option("--automated/--prepare-only")] = True,
    select_result: Annotated[
        bool, typer.Option(help="Select this exact completed result.")
    ] = False,
    activate_release: Annotated[bool, typer.Option(help="Activate the retained release.")] = False,
    json: JsonOpt = False,
) -> None:
    """Resume the run using its retained source and release binding."""
    from corpus_structure.cli.regenerate import regenerate

    regenerate(
        ctx,
        project=project,
        resume_run=run_id,
        automated=automated,
        select_result=select_result,
        activate=activate_release,
        json=json,
    )


@run_app.command("finalize")
def run_finalize(
    ctx: typer.Context,
    run_id: Annotated[int, typer.Argument(metavar="RUN")],
    output_realization: Annotated[str, typer.Option(help="Fresh evaluated realization identity.")],
    json: JsonOpt = False,
) -> None:
    """Seal completed automated work and publish its evaluated semantic realization."""
    from pydantic import RootModel

    from corpus_structure.orchestrate import commands
    from corpus_structure.semantic.domain_operations import DomainResult

    settings = state(ctx).settings()
    with _refusals(json), ENGINE(settings) as engine:
        result = commands.finalize_bound_run(
            engine, run_id, output_realization, analytics=settings.analytics
        )
    emit(RootModel[DomainResult](result), json=json)


# --- ci tasks ---------------------------------------------------------------------------------


def _render_tasks(result: BaseModel) -> RenderableType:
    from corpus_structure.orchestrate.commands import TaskListing

    assert isinstance(result, TaskListing)
    table = Table(
        "id",
        "stage",
        "unit",
        "configuration",
        "status",
        "reason",
        "rule",
        "cost",
        title=f"run {result.run_id} tasks",
    )
    for t in result.tasks:
        table.add_row(
            str(t.id),
            t.stage,
            t.unit_key or "",
            t.config,
            t.status,
            t.reason or "",
            t.rule_key or "",
            str(t.cost) if t.cost else "",
        )
    beyond = result.total - len(result.tasks)
    if beyond <= 0:
        return table
    return Group(table, Text(f"{beyond} more match (showing {len(result.tasks)})", style="yellow"))


def tasks(
    ctx: typer.Context,
    run_id: Annotated[int | None, typer.Argument(metavar="[RUN]")] = None,
    project: Annotated[
        str | None, typer.Option(help="Project (default: runtime.default_project).")
    ] = None,
    status: Annotated[list[TaskStatus] | None, typer.Option(help="Only this status.")] = None,
    method: Annotated[list[str] | None, typer.Option(help="Only this method.")] = None,
    limit: Annotated[int, typer.Option(help="At most this many.")] = 50,
    semantic: Annotated[bool, typer.Option(hidden=True)] = False,
    json: JsonOpt = False,
) -> None:
    """List a run's tasks (the latest run by default)."""
    from corpus_structure.orchestrate import commands

    with _refusals(json), READ_ENGINE(state(ctx).settings()) as engine, engine.connect() as conn:
        listing = commands.bound_task_listing(
            conn,
            run_id,
            project_id=project
            or (state(ctx).settings().runtime.default_project if run_id is None else None),
            statuses=status or (),
            methods=method or (),
            limit=limit,
        )
    emit(listing, json=json, render=_render_tasks)


def ingest(
    ctx: typer.Context,
    domain: Annotated[str | None, typer.Option(help="Choose an ambiguous executable pack.")] = None,
    corpus: Annotated[Path | None, typer.Option(exists=True, file_okay=False)] = None,
    project: str | None = None,
    semantic_release: Annotated[str | None, typer.Option(help="Already admitted release.")] = None,
    realization: Annotated[str | None, typer.Option(help="Exact bound input realization.")] = None,
    slice: str | None = None,
    scope: str | None = None,
    whole_document: Annotated[
        bool, typer.Option(help="Explicitly select all native sections and residual content.")
    ] = False,
    source_membership: Annotated[
        Literal["direct", "descendants"] | None,
        typer.Option(help="Exact native section membership."),
    ] = None,
    native_source: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    integrated_source: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    enrichment_options: Annotated[
        Path | None,
        typer.Option(
            help="Frozen primary characterization method-options JSON; enrich after capture.",
            exists=True,
            dir_okay=False,
        ),
    ] = None,
    json: JsonOpt = False,
) -> None:
    """Prepare a source cut for an existing bound project."""
    from corpus_structure.cli.regenerate import read_product_pin
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.orchestrate import commands
    from corpus_structure.orchestrate.project import init_bound_project
    from corpus_structure.semantic.runtime import resolve_source_binding

    if whole_document and (slice is not None or scope is not None):
        raise typer.BadParameter("whole-document is mutually exclusive with slice and scope")
    with _refusals(json), ENGINE(settings := state(ctx).settings()) as engine:
        project = project or settings.runtime.default_project
        if native_source is not None and integrated_source is not None:
            raise commands.CommandError(
                "native-source and integrated-source are mutually exclusive"
            )
        native_product = read_product_pin(native_source, "native")
        integrated_product = read_product_pin(integrated_source, "integrated")
        with engine.begin() as conn:
            release, source = resolve_source_binding(
                conn, project, release_id=semantic_release, realization_id=realization
            )
            domain = commands.resolve_source_domain(conn, project, release, domain)
            if corpus is not None:
                init_bound_project(
                    conn,
                    domain=domain,
                    corpus=corpus,
                    release_id=release,
                    realization_id=source,
                    name=project,
                    native_product=native_product,
                    integrated_product=integrated_product,
                )
        from corpus_structure.semantic.execution_preparation import prepare_execution

        with engine.connect() as conn:
            execution = prepare_execution(conn, release)
        with execution:
            result = commands._start_bound_run(
                execution,
                engine,
                release_id=release,
                realization_id=source,
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
                whole_document=whole_document,
                source_membership=source_membership,
                native_product=native_product,
                integrated_product=integrated_product,
                source_only=True,
            )
            if enrichment_options is not None:
                from dataclasses import asdict

                from pydantic import RootModel

                from corpus_structure.orchestrate.characterization import _characterize_captured_run

                enriched = _characterize_captured_run(
                    execution,
                    engine,
                    result,
                    project_id=project,
                    release_id=release,
                    realization_id=source,
                    domain=domain,
                    method_settings=MethodSettings(
                        data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache
                    ),
                    method_options=__import__("json").loads(enrichment_options.read_bytes()),
                )
                result = RootModel[dict](
                    dict(
                        capture=result.model_dump(mode="json"),
                        enrichment=[asdict(value) for value in enriched],
                    )
                )
    emit(result, json=json)


@run_app.command("parsers")
def run_parsers_command(
    ctx: typer.Context,
    request: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    json: JsonOpt = False,
) -> None:
    """Run bounded private parser scopes over exact retained development source."""
    from corpus_structure.orchestrate.pm2_stage import ParserRunRequest, run_parsers

    settings = state(ctx).settings()
    with _refusals(json):
        selection = ParserRunRequest.model_validate_json(request.read_bytes())
        with ENGINE(settings) as engine:
            result = run_parsers(engine, settings, selection)
    emit(result, json=json)


@run_app.command("interpret")
def run_interpretation_command(
    ctx: typer.Context,
    request: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    json: JsonOpt = False,
) -> None:
    """Run named private interpretation questions over exact retained development source."""
    from corpus_structure.orchestrate.pm2_stage import InterpretationRunRequest, run_interpretation

    settings = state(ctx).settings()
    with _refusals(json):
        selection = InterpretationRunRequest.model_validate_json(request.read_bytes())
        with ENGINE(settings) as engine:
            result = run_interpretation(engine, settings, selection)
    emit(result, json=json)


def register(app: typer.Typer) -> None:
    from corpus_structure.cli.status import status

    run_app.command("status")(status)
    app.command("ingest")(ingest)
    app.add_typer(project_app, name="project")
    app.add_typer(run_app, name="run")
    app.command("tasks")(tasks)


@run_app.command("characterize")
def run_characterize_command(
    ctx: typer.Context,
    request: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    json: JsonOpt = False,
) -> None:
    """Fulfil a frozen enriched-document demand from exact completed source pins."""
    from dataclasses import asdict

    from pydantic import RootModel

    from corpus_structure.core.method import MethodSettings
    from corpus_structure.orchestrate.characterization import (
        CharacterizationDemandRequest,
        execute_characterization_demand,
    )

    settings = state(ctx).settings()
    with _refusals(json), ENGINE(settings) as engine:
        demand = CharacterizationDemandRequest.model_validate_json(request.read_bytes())
        result = execute_characterization_demand(
            engine,
            demand,
            MethodSettings(
                data_dir=settings.paths.data_dir,
                model_cache=settings.paths.model_cache,
                nemotron_endpoint=settings.nemotron.endpoint,
                nemotron_python=settings.nemotron.python,
                nemotron_worker=settings.nemotron.worker,
                nemotron_receipts=settings.nemotron.receipts,
                nemotron_timeout_seconds=settings.nemotron.timeout_seconds,
            ),
        )
    emit(RootModel[dict](asdict(result)), json=json)
