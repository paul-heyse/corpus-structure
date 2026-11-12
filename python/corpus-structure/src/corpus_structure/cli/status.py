"""`ci status [RUN]`: run progress (orchestration §3.13, P0-O-1) and the resolved settings
(foundations). Progress is the run's task counts per stage by status and reason, its cut and final
M19 task once sealed and agent tasks unresolved as of the cut; the latest run
by default. Without a reachable database the settings are still reported, with the reason."""

from __future__ import annotations

from typing import Annotated, Any

import typer
from pydantic import BaseModel
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.output import JsonOpt, cli_settings_report, emit, safe_text, state
from corpus_structure.settings import SettingsReport


def _render(result: BaseModel) -> RenderableType:
    assert isinstance(result, SettingsReport)
    table = Table("setting", "value", title="settings")
    for name, value in result.resolved.items():
        table.add_row(Text(safe_text(name)), Text(safe_text(value)))
    if not result.unknown_env:
        return table
    unknown = Text(
        "unknown CORPUS_* variables (set nothing): " + safe_text(", ".join(result.unknown_env)),
        style="yellow",
    )
    return Group(table, unknown)


class StatusResult(BaseModel):
    """`ci status`: the run's progress (None without a run or a database) and the settings."""

    progress: Any = None  # orchestrate.commands.StatusReport
    database_error: str | None = None
    settings: SettingsReport


def _render_status(result: BaseModel) -> RenderableType:
    assert isinstance(result, StatusResult)
    parts: list[RenderableType] = []
    progress = result.progress
    if result.database_error is not None:
        parts.append(Text(f"no run progress: {result.database_error}", style="yellow"))
    elif progress is not None and progress.run is None:
        parts.append(Text("no runs yet"))
    elif progress is not None:
        run = progress.run
        head = Table("field", "value", title=f"run {run.run_id}")
        for name in (
            "kind",
            "status",
            "release_id",
            "cut_id",
            "cut_name",
            "output_realization_id",
            "unresolved_agent_tasks",
            "readiness",
            "supervisor",
        ):
            head.add_row(name, Text(safe_text(str(getattr(run, name)))))
        stages = Table("stage", "status", "reason", "tasks", title="tasks")
        for c in run.stages:
            stages.add_row(
                Text(safe_text(c.stage)),
                Text(safe_text(c.status)),
                Text(safe_text(c.reason or "")),
                str(c.count),
            )
        parts += [head, stages]
        if run.operation is not None:
            from corpus_structure.cli.result_inspection import render_operation

            parts.append(render_operation(run.operation))
        elif run.operation_unavailable_reason:
            parts.append(Text(run.operation_unavailable_reason))
    if progress is not None and progress.orphaned is None:
        parts.append(Text("orphan assessment: not assessed"))
    if progress is not None and progress.orphaned:
        orphaned = ", ".join(map(str, progress.orphaned))
        parts.append(Text(f"orphaned runs: {orphaned} (`ci run cancel RUN`)", style="yellow"))
    parts.append(_render(result.settings))
    return Group(*parts)


def status(
    ctx: typer.Context,
    run_id: Annotated[int | None, typer.Argument(metavar="[RUN]")] = None,
    project: Annotated[
        str | None, typer.Option(help="Project (default: runtime.default_project).")
    ] = None,
    semantic: Annotated[bool, typer.Option(hidden=True)] = False,
    operation_after: Annotated[
        str | None,
        typer.Option(help="Continue native operation progress using its returned cursor."),
    ] = None,
    operation_limit: Annotated[
        int, typer.Option(min=1, max=32, help="Regions per native operation page.")
    ] = 8,
    json: JsonOpt = False,
) -> None:
    """Show a run's progress (the latest by default) and the resolved settings."""
    from psycopg import OperationalError
    from psycopg_pool import PoolTimeout

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.orchestrate import commands

    with failure_boundary(json, expected=(commands.CommandError, ValueError)):
        from corpus_structure.orchestrate.source_progress import OperationProgressCursor
        from corpus_structure.semantic.query import read_snapshot

        if operation_after is not None:
            OperationProgressCursor.decode(operation_after)
        settings = state(ctx).settings()
        report = cli_settings_report(settings)
        try:
            with orchestrate.READ_ENGINE(settings) as engine, read_snapshot(engine) as conn:
                progress = commands.bound_status(
                    conn,
                    run_id,
                    operation_cursor=operation_after,
                    operation_region_limit=operation_limit,
                    project_id=project
                    or (settings.runtime.default_project if run_id is None else None),
                )
        except (PoolTimeout, OperationalError) as error:
            result = StatusResult(
                database_error=f"{type(error).__name__}: {safe_text(str(error))}", settings=report
            )
        else:
            result = StatusResult(progress=progress, settings=report)
    emit(result, json=json, render=_render_status)


def register(app: typer.Typer) -> None:
    app.command("status")(status)
