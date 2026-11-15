"""Resolved settings and an explicitly selected native demand frontier."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import BaseModel
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.output import JsonOpt, cli_settings_report, emit, safe_text, state, write_report_text
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
    """Settings are local; demand progress requires an explicit target."""

    progress: dict[str, Any] | None = None
    database_error: str | None = None
    settings: SettingsReport


def _render_status(result: BaseModel) -> RenderableType:
    assert isinstance(result, StatusResult)
    parts: list[RenderableType] = []
    if result.database_error is not None:
        parts.append(Text(f"demand progress unavailable: {result.database_error}", style="yellow"))
    elif result.progress is not None:
        head = Table("field", "value", title="selected demand")
        for name in ("cut_id", "state", "complete", "continuation"):
            head.add_row(name, Text(safe_text(str(result.progress.get(name)))))
        parts.append(head)
        rows = Table("obligation", "state", title="demand frontier")
        for obligation in result.progress["obligations"]:
            rows.add_row(str(obligation["obligation_id"]), str(obligation["fate"]))
        parts.append(rows)
    else:
        parts.append(Text("Select --demand and --project to inspect native progress."))
    parts.append(_render(result.settings))
    return Group(*parts)


def status(
    ctx: typer.Context,
    demand: Annotated[str | None, typer.Option(help="Exact native demand; no latest-run lookup.")] = None,
    project: Annotated[str | None, typer.Option(help="Exact demand project.")] = None,
    continuation: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    limit: Annotated[int, typer.Option(min=1, max=1000)] = 100,
    json: JsonOpt = False,
) -> None:
    """Show resolved settings and optionally one pinned native demand frontier."""
    from psycopg import OperationalError
    from psycopg_pool import PoolTimeout

    from corpus_structure.cli import orchestrate
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
    from corpus_structure.semantic.demand_results import read_demand_result

    with failure_boundary(json, expected=(ValueError, OSError)):
        if bool(demand) != bool(project) or (continuation is not None and demand is None):
            raise ValueError("demand progress requires both --demand and --project")
        settings = state(ctx).settings()
        report = cli_settings_report(settings)
        result = StatusResult(settings=report)
        if demand is not None and project is not None:
            pins = None if continuation is None else wire_json_loads(continuation.read_bytes())
            if pins is not None and not isinstance(pins, dict):
                raise ValueError("continuation must be a native cursor object")
            try:
                with orchestrate.READ_ENGINE(settings) as engine, engine.begin() as connection:
                    page = read_demand_result(connection, demand, project_id=project,
                                              continuation=pins, limit=limit, view="frontier")
                    result.progress = page.report()
            except (PoolTimeout, OperationalError) as error:
                result.database_error = f"{type(error).__name__}: {safe_text(str(error))}"
    if json:
        write_report_text(json_bytes(result.model_dump(mode="python")).decode() + "\n")
    else:
        emit(result, json=False, render=_render_status)


def register(app: typer.Typer) -> None:
    app.command("status")(status)
