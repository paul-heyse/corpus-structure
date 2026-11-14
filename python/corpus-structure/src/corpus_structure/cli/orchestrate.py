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

from corpus_structure.cli.characterization_options import (
    method_settings as resolved_method_settings,
)
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
    from corpus_structure.orchestrate.source_request import validate_source_roles

    try:
        validate_source_roles(native_source, integrated_source)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    if semantic_release is None or realization is None:
        raise typer.BadParameter("initialization requires --semantic-release and --realization")
    native_product = read_product_pin(native_source, "native")
    integrated_product = read_product_pin(integrated_source, "integrated")
    settings = state(ctx).settings()
    seams = PHASE0()
    with _refusals(json), ENGINE(settings) as engine, engine.begin() as conn:
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
        str | None, typer.Option(help="Method pack for explicit semantic source execution.")
    ] = None,
    extraction_policy: Annotated[
        Literal["phase0", "m1-candidate"],
        typer.Option(help="Explicit source policy: phase0 or m1-candidate."),
    ] = "phase0",
    m1_configuration: Annotated[
        Literal["default", "described", "readings", "contextual", "source-only"],
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
    demand: Annotated[
        str | None, typer.Option(help="Execute or resume this exact frozen native demand.")
    ] = None,
    source_root: Annotated[
        Path | None,
        typer.Option(
            exists=True, file_okay=False, help="Explicit executable source root for --demand."
        ),
    ] = None,
    json: JsonOpt = False,
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
) -> None:
    """Start a run over the project's corpus and run it to its end."""
    if ctx.invoked_subcommand is not None:
        return
    if demand is not None:
        if source_root is None:
            raise typer.BadParameter("--demand requires --source-root")
        if (
            any(
                value is not None
                for value in (
                    slice,
                    scope,
                    corpus,
                    agent_mode,
                    agent_reuse,
                    gpu_mode,
                    semantic_release,
                    realization,
                    domain,
                    record_policy,
                    integrated_product_task,
                    integrated_product_key,
                    integrated_product_digest,
                )
            )
            or whole_document
            or source_membership is not None
            or fresh
            or characterization_view
            or phase != 0
            or extraction_policy != "phase0"
            or m1_configuration != "default"
        ):
            raise typer.BadParameter(
                "native demand execution consumes retained intent; source-selection and workflow overrides require a new demand"
            )
        from .demands import execute

        execute(
            ctx,
            demand,
            source_root=source_root,
            project=project,
            execution_policy=execution_policy,
            json=json,
        )
        return
    if source_root is not None:
        raise typer.BadParameter("--source-root requires --demand")
    from corpus_structure.orchestrate.source_operation import (
        preflight_source_operation,
        run_source_operation,
    )
    from corpus_structure.orchestrate.source_request import (
        SourceRunRequest,
        integrated_product_pin,
        source_selection,
        source_workflow,
    )
    from corpus_structure.semantic.product_reference import ProductReference

    settings = state(ctx).settings()
    method_settings = resolved_method_settings(settings, execution_policy)
    try:
        request = SourceRunRequest(
            project_id=project or settings.runtime.default_project,
            release_id=semantic_release,
            realization_id=realization,
            domain=domain,
            selection=source_selection(
                slice=slice, scope=scope, whole_document=whole_document, corpus=corpus
            ),
            workflow=source_workflow(
                extraction_policy=extraction_policy,
                m1_configuration=m1_configuration,
                record_policy=loads(record_policy.read_bytes()) if record_policy else None,
                characterization_views=tuple(
                    ProductReference(**loads(value)) for value in characterization_view or ()
                ),
            ),
            integrated_product=integrated_product_pin(
                integrated_product_task, integrated_product_key, integrated_product_digest
            ),
            membership=source_membership,
            fresh=tuple(fresh or ()),
            phase=phase,
            agent_mode=str(agent_mode or AgentMode.COMPLETE),
            agent_reuse=str(agent_reuse or AgentReuse.FULL),
        )
        seams = PHASE0()
        dependencies = {"domains": seams["domains"]}
        if extraction_policy == "phase0":
            dependencies.update(graph=seams["graph"], registry_for=seams["registry_for"])
        preflight_source_operation(
            request,
            method_settings,
            **{key: value for key, value in dependencies.items() if key != "domains"},
        )
    except (OSError, TypeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    if gpu_mode is not None:
        raise typer.BadParameter("the selected semantic graph has no GPU operation")
    from pydantic import RootModel

    from corpus_structure.cli.managed import result_store
    from corpus_structure.orchestrate.source_reporting import record_source_run

    with (
        result_store(ctx).operation(
            "run", scope={"project": request.project_id}, observations=True
        ) as invocation,
        _refusals(json),
        ENGINE(settings) as engine,
    ):
        report = run_source_operation(
            engine,
            request,
            method_settings,
            on_created=lambda created: record_source_run(invocation, engine, created),
            **dependencies,
        )
    emit(
        RootModel[dict]({**report.model_dump(mode="json"), "invocation_id": invocation.id}),
        json=json,
    )


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
    characterization: Annotated[
        bool, typer.Option(help="Recover the frozen multi-stage characterization demand.")
    ] = False,
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
) -> None:
    """Resume the run using its retained source and release binding."""
    if characterization:
        if not automated or select_result or activate_release:
            raise typer.BadParameter(
                "characterization recovery produces exact views; "
                "use ordinary result selection separately"
            )
        from dataclasses import asdict

        from pydantic import RootModel

        from corpus_structure.cli.managed import result_store
        from corpus_structure.orchestrate.characterization_recovery import (
            record_characterization_run,
            resume_characterization,
        )
        from corpus_structure.orchestrate.source_reporting import record_recovery_binding

        settings = state(ctx).settings()
        method_settings = resolved_method_settings(settings, execution_policy)
        with (
            result_store(ctx).operation(
                "run.resume", scope={"run_id": run_id, "characterization": True}, observations=True
            ) as invocation,
            _refusals(json),
            ENGINE(settings) as engine,
        ):
            results = resume_characterization(
                engine,
                run_id,
                method_settings,
                project_id=project,
                on_created=lambda created: record_characterization_run(invocation, engine, created),
                on_frozen=lambda anchor, envelope: record_recovery_binding(
                    invocation, engine, anchor, envelope, method_settings.execution_policy
                ),
            )
            report = RootModel[dict](
                dict(invocation_id=invocation.id, enrichment=[asdict(value) for value in results])
            )
        emit(report, json=json)
        return
    from corpus_structure.cli.regenerate import regenerate

    regenerate(
        ctx,
        project=project,
        resume_run=run_id,
        automated=automated,
        select_result=select_result,
        activate=activate_release,
        execution_policy=execution_policy,
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
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
) -> None:
    """Prepare a source cut for an existing bound project."""
    from corpus_structure.cli.managed import result_store
    from corpus_structure.cli.regenerate import read_product_pin
    from corpus_structure.orchestrate.source_operation import (
        preflight_source_operation,
        run_source_operation,
    )
    from corpus_structure.orchestrate.source_reporting import record_source_run
    from corpus_structure.orchestrate.source_request import (
        Capture,
        CharacterizationOptions,
        SourceRunRequest,
        source_selection,
        validate_source_roles,
    )

    settings = state(ctx).settings()
    method_settings = resolved_method_settings(settings, execution_policy)
    try:
        validate_source_roles(native_source, integrated_source)
        request = SourceRunRequest(
            project_id=project or settings.runtime.default_project,
            release_id=semantic_release,
            realization_id=realization,
            domain=domain,
            selection=source_selection(slice=slice, scope=scope, whole_document=whole_document),
            workflow=Capture(
                CharacterizationOptions.from_options(loads(enrichment_options.read_bytes()))
                if enrichment_options
                else None
            ),
            membership=source_membership,
            registration_corpus=corpus,
            native_product=read_product_pin(native_source, "native"),
            integrated_product=read_product_pin(integrated_source, "integrated"),
        )
        preflight_source_operation(request, method_settings)
    except (OSError, TypeError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error
    with (
        result_store(ctx).operation(
            "ingest", scope={"project": request.project_id}, observations=True
        ) as invocation,
        _refusals(json),
        ENGINE(settings) as engine,
    ):
        result = run_source_operation(
            engine,
            request,
            method_settings,
            on_created=lambda created: record_source_run(invocation, engine, created),
        )
    from pydantic import RootModel

    emit(
        RootModel[dict]({**result.model_dump(mode="json"), "invocation_id": invocation.id}),
        json=json,
    )


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
    request: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    captured_run: Annotated[
        int | None, typer.Option(help="Reuse this exact completed capture; no recognition.")
    ] = None,
    release: Annotated[
        str | None, typer.Option(help="Target admitted execution release for retained capture.")
    ] = None,
    realization: Annotated[str | None, typer.Option(help="Exact target input realization.")] = None,
    method_options: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    fresh: Annotated[
        list[str] | None, typer.Option(help="Fresh primary producers for this new demand.")
    ] = None,
    json: JsonOpt = False,
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
) -> None:
    """Fulfil a frozen demand or enrich an exact retained capture without recognition."""
    from dataclasses import asdict
    from types import SimpleNamespace

    from pydantic import RootModel
    from sqlalchemy import select

    from corpus_structure.cli.managed import result_store
    from corpus_structure.orchestrate.characterization import (
        CharacterizationDemandRequest,
        characterize_captured_run,
        execute_characterization_demand,
    )
    from corpus_structure.orchestrate.characterization_recovery import record_characterization_run
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.runtime import resolve_source_binding

    if (request is None) == (captured_run is None):
        raise typer.BadParameter("select exactly one of --request and --captured-run")
    if request is not None and (
        release is not None or realization is not None or method_options is not None or fresh
    ):
        raise typer.BadParameter("--request owns its release, source and method selections")
    settings = state(ctx).settings()
    method_settings = resolved_method_settings(settings, execution_policy)
    demand = (
        CharacterizationDemandRequest.model_validate_json(request.read_bytes())
        if request is not None
        else None
    )
    from corpus_structure.orchestrate.source_request import CharacterizationOptions

    parsed_options = (
        CharacterizationOptions.from_options(loads(method_options.read_bytes())).options()
        if method_options
        else {}
    )
    with (
        result_store(ctx).operation(
            "run.characterize",
            scope={"request": str(request) if request else None, "captured_run": captured_run},
            observations=True,
        ) as invocation,
        _refusals(json),
        ENGINE(settings) as engine,
    ):

        def callback(created):
            record_characterization_run(invocation, engine, created)

        if request is not None:
            assert demand is not None
            result = execute_characterization_demand(
                engine, demand, method_settings, on_created=callback
            )
            report = {**asdict(result), "invocation_id": invocation.id}
        else:
            with engine.connect() as conn:
                runs = table("ops.run")
                origin = (
                    conn.execute(select(runs).where(runs.c.id == captured_run)).mappings().one()
                )
                if origin["status"] != "finished" or not origin["sealed"]:
                    raise OperationConflict("--captured-run requires a completed original capture")
                target_release = release or origin["release_id"]
                target_realization = realization or (
                    origin["input_realization_id"]
                    if target_release == origin["release_id"]
                    else None
                )
                target_release, target_realization = resolve_source_binding(
                    conn,
                    origin["project_id"],
                    release_id=target_release,
                    realization_id=target_realization,
                )
                domain = origin["options"].get("domain")
                if not domain:
                    raise OperationConflict("captured run has no frozen domain selection")
            values = characterize_captured_run(
                engine,
                SimpleNamespace(run_id=captured_run),
                project_id=origin["project_id"],
                release_id=target_release,
                realization_id=target_realization,
                domain=domain,
                method_settings=method_settings,
                method_options=parsed_options,
                fresh_methods=tuple(fresh or ()),
                on_created=callback,
            )
            report = dict(
                invocation_id=invocation.id,
                capture_run_id=captured_run,
                enrichment=[asdict(value) for value in values],
            )
    emit(RootModel[dict](report), json=json)
