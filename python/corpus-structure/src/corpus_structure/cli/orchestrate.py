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
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import BaseModel
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.output import JsonOpt, emit, state, stderr_console
from corpus_structure.core.vocab import AgentMode, AgentReuse, GpuMode, TaskStatus

project_app = typer.Typer(help="Create the project from a pack and corpus.", no_args_is_help=True)
run_app = typer.Typer(help="Start or cancel a run.", invoke_without_command=True)


@contextmanager
def _open_engine(settings: Any, timeout: float = 30.0) -> Generator[Any]:
    from corpus_structure.semantic.runtime import open_runtime_engine

    with open_runtime_engine(settings, timeout=timeout, purpose="write") as engine:
        yield engine


ENGINE: Callable[..., Any] = _open_engine


def _phase0() -> dict[str, Any]:
    from corpus_structure.orchestrate import phase0
    from corpus_structure.schema.pack import DOMAINS

    return {
        "registry_for": phase0.registry,
        "graph": phase0.PHASE0,
        "domains": DOMAINS,
    }


PHASE0: Callable[[], dict[str, Any]] = _phase0


@contextmanager
def _refusals() -> Generator[None]:
    from corpus_structure.orchestrate import commands, project, registry
    from corpus_structure.orchestrate.errors import RunError
    from corpus_structure.orchestrate.policy import PolicyError
    from corpus_structure.orchestrate.slices import SliceError
    from corpus_structure.semantic.domain_operations import DomainOperationRefused
    from corpus_structure.semantic.operations import OperationConflict

    try:
        yield
    except (
        commands.CommandError,
        project.ProjectError,
        registry.RegistryError,
        RunError,
        OperationConflict,
        DomainOperationRefused,
        SliceError,
        PolicyError,
    ) as error:
        stderr_console().print(f"refused: {error}")
        raise typer.Exit(code=1) from None


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
    json: JsonOpt = False,
) -> None:
    """Create or update the project: its documents and the pack's versions."""
    from corpus_structure.orchestrate import project

    settings = state(ctx).settings()
    seams = PHASE0()
    with _refusals(), ENGINE(settings) as engine, engine.begin() as conn:
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
    corpus: Annotated[str | None, typer.Option(help="Ingest a named corpus slice.")] = None,
    agent_mode: Annotated[AgentMode | None, typer.Option(help="wait or complete.")] = None,
    agent_reuse: Annotated[AgentReuse | None, typer.Option(help="full or by_unit.")] = None,
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
    json: JsonOpt = False,
) -> None:
    """Start a run over the project's corpus and run it to its end."""
    if ctx.invoked_subcommand is not None:
        return
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.orchestrate import commands

    settings = state(ctx).settings()
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
    with _refusals(), ENGINE(settings) as engine:
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
            corpus=corpus,
            agent_mode=str(agent_mode or AgentMode.COMPLETE),
            agent_reuse=str(agent_reuse or AgentReuse.FULL),
            **{k: v for k, v in PHASE0().items() if k in {"registry_for", "graph", "domains"}},
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

    with _refusals(), ENGINE(state(ctx).settings()) as engine:
        report = commands.cancel_bound_run(engine, run_id)
    emit(report, json=json, render=lambda r: _table("cancelled", r))


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
    with _refusals(), ENGINE(settings) as engine:
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

    with _refusals(), ENGINE(state(ctx).settings()) as engine, engine.connect() as conn:
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


def register(app: typer.Typer) -> None:
    app.add_typer(project_app, name="project")
    app.add_typer(run_app, name="run")
    app.command("tasks")(tasks)
