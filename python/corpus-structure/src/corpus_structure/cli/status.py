"""`ci status [RUN]`: run progress (orchestration §3.13, P0-O-1) and the resolved settings
(foundations). Progress is the run's task counts per stage by status and reason, its cut and final
M19 task once sealed, agent tasks unresolved as of the cut, and the orphaned runs; the latest run
by default. Without a reachable database the settings are still reported, with the reason."""

from __future__ import annotations

import os
from typing import Annotated, Any

import typer
from pydantic import BaseModel
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.output import JsonOpt, emit, state, stderr_console
from corpus_structure.settings import SettingsReport, settings_report


def _render(result: BaseModel) -> RenderableType:
    assert isinstance(result, SettingsReport)
    table = Table("setting", "value", title="settings")
    for name, value in result.resolved.items():
        table.add_row(name, value)
    if not result.unknown_env:
        return table
    unknown = Text(
        "unknown CORPUS_* variables (set nothing): " + ", ".join(result.unknown_env), style="yellow"
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
            "started_at",
            "cut_at",
            "cut_m19_task_id",
            "finished_at",
            "unresolved_agent_tasks",
        ):
            head.add_row(name, str(getattr(run, name)))
        stages = Table("stage", "status", "reason", "tasks", title="tasks")
        for c in run.stages:
            stages.add_row(c.stage, c.status, c.reason or "", str(c.count))
        parts += [head, stages]
    if progress is not None and progress.orphaned:
        orphaned = ", ".join(map(str, progress.orphaned))
        parts.append(Text(f"orphaned runs: {orphaned} (`ci run cancel RUN`)", style="yellow"))
    parts.append(_render(result.settings))
    return Group(*parts)


def status(
    ctx: typer.Context,
    run_id: Annotated[int | None, typer.Argument(metavar="[RUN]")] = None,
    json: JsonOpt = False,
) -> None:
    """Show a run's progress (the latest by default) and the resolved settings."""
    from corpus_structure.cli import orchestrate
    from corpus_structure.orchestrate import commands

    settings = state(ctx).settings()
    report = settings_report(settings, os.environ)
    from psycopg import OperationalError
    from psycopg_pool import PoolTimeout

    try:
        with orchestrate.ENGINE(settings, timeout=5.0) as engine, engine.connect() as conn:
            progress = commands.status(conn, run_id)
    except commands.CommandError as error:
        stderr_console().print(f"refused: {error}")
        raise typer.Exit(code=1) from None
    except (PoolTimeout, OperationalError) as error:  # unreachable: the settings still report
        result = StatusResult(database_error=f"{type(error).__name__}: {error}", settings=report)
    else:
        result = StatusResult(progress=progress, settings=report)
    emit(result, json=json, render=_render_status)


def register(app: typer.Typer) -> None:
    app.command("status")(status)
