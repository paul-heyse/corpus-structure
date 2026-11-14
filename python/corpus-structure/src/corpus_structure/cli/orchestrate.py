"""Ordinary source commands compile explicit choices into native demand custody."""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from pydantic import BaseModel
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.output import JsonOpt, emit, state
from corpus_structure.core.vocab import TaskStatus

project_app = typer.Typer(
    help="Register a project and immutable original documents.", no_args_is_help=True
)
run_app = typer.Typer(
    help="Execute or inspect immutable native demands.", invoke_without_command=True
)


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


def _refusals(json: bool):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.refusals import SemanticRefusal

    return failure_boundary(json, expected=(ValueError, KeyError, OSError, SemanticRefusal))


def _table(title: str, result: BaseModel) -> Table:
    table = Table("field", "value", title=title)
    for name, value in result.model_dump(mode="json").items():
        table.add_row(name, str(value))
    return table


@project_app.command("init")
def project_init(
    ctx: typer.Context,
    domain: Annotated[str, typer.Option(help="The pack under domains/.")],
    corpus: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    semantic_release: Annotated[str, typer.Option(help="Already admitted semantic release.")],
    realization: Annotated[str, typer.Option(help="Explicit empty realization identity.")],
    name: Annotated[str | None, typer.Option()] = None,
    json: JsonOpt = False,
) -> None:
    """Register configured immutable originals without starting inference."""
    from corpus_structure.orchestrate import project

    settings = state(ctx).settings()
    with _refusals(json), ENGINE(settings) as engine, engine.begin() as connection:
        report = project.init_bound_project(
            connection,
            domain=domain,
            corpus=corpus,
            release_id=semantic_release,
            realization_id=realization,
            name=name or settings.runtime.default_project,
        )
    emit(report, json=json, render=lambda value: _table("project", value))


def execute_source_choices(
    ctx,
    *,
    action,
    workflow,
    source_root,
    request=None,
    project=None,
    semantic_release=None,
    runtime=None,
    domain=None,
    slice=None,
    scope=None,
    whole_document=False,
    source_membership="descendants",
    document=None,
    source=None,
    target=None,
    operation_options=None,
    execution_profile="source-native",
    execution_policy=None,
    json=False,
):
    from corpus_structure.orchestrate.source_request import (
        RetainedSourceSelection,
        SourceRunRequest,
        source_selection,
    )
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import DemandOperationSelection

    from .demands import execute_request

    if request is not None:
        if (
            any(
                value is not None
                for value in (
                    semantic_release,
                    runtime,
                    domain,
                    slice,
                    scope,
                    operation_options,
                )
            )
            or whole_document
            or document
            or source
            or target
            or source_membership != "descendants"
        ):
            raise typer.BadParameter("--request owns its source and operation selections")
        with _refusals(json):
            parsed = SourceRunRequest.model_validate(json_loads(request.read_bytes()))
            if parsed.workflow != workflow:
                raise ValueError("request workflow differs from the selected command")
    else:
        if semantic_release is None or runtime is None:
            raise typer.BadParameter("new source demands require --semantic-release and --runtime")
        with _refusals(json):
            parsed = SourceRunRequest(
                project_id=project or state(ctx).settings().runtime.default_project,
                release_id=semantic_release,
                runtime_id=runtime,
                domain=domain,
                selection=source_selection(slice=slice, scope=scope, whole_document=whole_document),
                workflow=workflow,
                membership=source_membership,
                documents=tuple(document or ()),
                retained_sources=tuple(
                    RetainedSourceSelection.model_validate(json_loads(value.read_bytes()))
                    for value in source or ()
                ),
                targets=tuple(target or ()),
                selections=tuple(
                    DemandOperationSelection.model_validate(value)
                    for value in (
                        json_loads(operation_options.read_bytes())
                        if operation_options is not None
                        else ()
                    )
                ),
                execution_profile=execution_profile,
            )
    execute_request(
        ctx,
        source_request=parsed,
        source_root=source_root,
        project=project,
        action=action,
        execution_policy=execution_policy,
        json=json,
    )


@run_app.callback()
def run(
    ctx: typer.Context,
    source_root: Annotated[Path | None, typer.Option(exists=True, file_okay=False)] = None,
    demand: Annotated[
        str | None, typer.Option(help="Execute or resume exact retained intent.")
    ] = None,
    request: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    project: Annotated[str | None, typer.Option()] = None,
    semantic_release: Annotated[str | None, typer.Option()] = None,
    runtime: Annotated[str | None, typer.Option(help="Exact admitted runtime profile.")] = None,
    domain: Annotated[str | None, typer.Option()] = None,
    slice: Annotated[str | None, typer.Option()] = None,
    scope: Annotated[str | None, typer.Option()] = None,
    whole_document: Annotated[bool, typer.Option()] = False,
    source_membership: Annotated[Literal["direct", "descendants"], typer.Option()] = "descendants",
    document: Annotated[
        list[str] | None, typer.Option(help="Exact registered document key; repeat.")
    ] = None,
    source: Annotated[
        list[Path] | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            help="Exact retained source reference and selectors JSON; repeat.",
        ),
    ] = None,
    target: Annotated[
        list[str] | None, typer.Option(help="Explicit declared operation target; repeat.")
    ] = None,
    operation_options: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    execution_profile: Annotated[str, typer.Option()] = "source-native",
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    json: JsonOpt = False,
) -> None:
    """Freeze ordinary source choices and execute their declared native closure."""
    if ctx.invoked_subcommand is not None:
        return
    if source_root is None:
        raise typer.BadParameter("execution requires --source-root for captured executable bytes")
    if demand is not None:
        if (
            request is not None
            or any(
                value is not None
                for value in (
                    semantic_release,
                    runtime,
                    domain,
                    slice,
                    scope,
                    operation_options,
                )
            )
            or whole_document
            or document
            or source
            or target
            or source_membership != "descendants"
            or execution_profile != "source-native"
        ):
            raise typer.BadParameter(
                "a retained demand owns its original source and workflow choices"
            )
        from .demands import execute_request

        execute_request(
            ctx,
            demand=demand,
            source_root=source_root,
            project=project,
            execution_policy=execution_policy,
            json=json,
        )
        return
    execute_source_choices(
        ctx,
        action="run",
        workflow="phase0",
        source_root=source_root,
        request=request,
        project=project,
        semantic_release=semantic_release,
        runtime=runtime,
        domain=domain,
        slice=slice,
        scope=scope,
        whole_document=whole_document,
        source_membership=source_membership,
        document=document,
        source=source,
        target=target,
        operation_options=operation_options,
        execution_profile=execution_profile,
        execution_policy=execution_policy,
        json=json,
    )


@run_app.command("cancel")
def run_cancel(
    ctx: typer.Context,
    demand: Annotated[str, typer.Argument(help="Exact native demand ID.")],
    reason: Annotated[str, typer.Option(help="Retained cancellation reason.")],
    json: JsonOpt = False,
) -> None:
    from .demands import cancel

    cancel(ctx, demand, reason=reason, json=json)


@run_app.command("resume")
def run_resume(
    ctx: typer.Context,
    demand: Annotated[
        str, typer.Argument(help="Exact native demand ID; historical run IDs are inspection only.")
    ],
    source_root: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    project: Annotated[str | None, typer.Option()] = None,
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    json: JsonOpt = False,
) -> None:
    from .demands import execute_request

    execute_request(
        ctx,
        demand=demand,
        source_root=source_root,
        project=project,
        execution_policy=execution_policy,
        json=json,
    )


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
    source_root: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    request: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    project: Annotated[str | None, typer.Option()] = None,
    semantic_release: Annotated[str | None, typer.Option()] = None,
    runtime: Annotated[str | None, typer.Option()] = None,
    domain: Annotated[str | None, typer.Option()] = None,
    slice: Annotated[str | None, typer.Option()] = None,
    scope: Annotated[str | None, typer.Option()] = None,
    whole_document: Annotated[bool, typer.Option()] = False,
    source_membership: Annotated[Literal["direct", "descendants"], typer.Option()] = "descendants",
    document: Annotated[list[str] | None, typer.Option()] = None,
    target: Annotated[list[str] | None, typer.Option()] = None,
    operation_options: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    json: JsonOpt = False,
) -> None:
    """Capture registered originals and discover the explicitly selected source scope."""
    execute_source_choices(
        ctx,
        action="ingest",
        workflow="capture",
        source_root=source_root,
        request=request,
        project=project,
        semantic_release=semantic_release,
        runtime=runtime,
        domain=domain,
        slice=slice,
        scope=scope,
        whole_document=whole_document,
        source_membership=source_membership,
        document=document,
        target=target,
        operation_options=operation_options,
        execution_policy=execution_policy,
        json=json,
    )


@run_app.command("characterize")
def run_characterize_command(
    ctx: typer.Context,
    source_root: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    request: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    project: Annotated[str | None, typer.Option()] = None,
    semantic_release: Annotated[str | None, typer.Option()] = None,
    runtime: Annotated[str | None, typer.Option()] = None,
    domain: Annotated[str | None, typer.Option()] = None,
    slice: Annotated[str | None, typer.Option()] = None,
    scope: Annotated[str | None, typer.Option()] = None,
    whole_document: Annotated[bool, typer.Option()] = False,
    source_membership: Annotated[Literal["direct", "descendants"], typer.Option()] = "descendants",
    document: Annotated[list[str] | None, typer.Option()] = None,
    source: Annotated[list[Path] | None, typer.Option(exists=True, dir_okay=False)] = None,
    target: Annotated[list[str] | None, typer.Option()] = None,
    operation_options: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    json: JsonOpt = False,
) -> None:
    """Characterize an exact retained source selection or explicit new capture."""
    execute_source_choices(
        ctx,
        action="run.characterize",
        workflow="characterize",
        source_root=source_root,
        request=request,
        project=project,
        semantic_release=semantic_release,
        runtime=runtime,
        domain=domain,
        slice=slice,
        scope=scope,
        whole_document=whole_document,
        source_membership=source_membership,
        document=document,
        source=source,
        target=target,
        operation_options=operation_options,
        execution_policy=execution_policy,
        json=json,
    )


def _execute_declared_request(ctx, request, source_root, action, execution_policy, json):
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest

    from .demands import execute_request

    with _refusals(json):
        selection = NativeDemandRequest.model_validate(json_loads(request.read_bytes()))
    execute_request(
        ctx,
        request=selection,
        source_root=source_root,
        action=action,
        execution_policy=execution_policy,
        json=json,
    )


@run_app.command("parsers")
def run_parsers_command(
    ctx: typer.Context,
    request: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    source_root: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    json: JsonOpt = False,
) -> None:
    """Execute declared parser profiles over the request's exact source population."""
    _execute_declared_request(ctx, request, source_root, "run.parsers", execution_policy, json)


@run_app.command("interpret")
def run_interpretation_command(
    ctx: typer.Context,
    request: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    source_root: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    execution_policy: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    json: JsonOpt = False,
) -> None:
    """Execute the frozen source/question/candidate interpretation selection."""
    _execute_declared_request(ctx, request, source_root, "run.interpret", execution_policy, json)


def register(app: typer.Typer) -> None:
    from corpus_structure.cli.status import status

    run_app.command("status")(status)
    app.command("ingest")(ingest)
    app.add_typer(project_app, name="project")
    app.add_typer(run_app, name="run")
    app.command("tasks")(tasks)
