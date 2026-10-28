"""`ci status` (orchestration, P0-O-1, adds run progress; foundations seeds the settings report)."""

from __future__ import annotations

import os

import typer
from pydantic import BaseModel
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from corpus_structure.cli.output import JsonOpt, emit, state
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


def status(ctx: typer.Context, json: JsonOpt = False) -> None:
    """Show the resolved settings (run progress arrives with orchestration)."""
    report = settings_report(state(ctx).settings(), os.environ)
    emit(report, json=json, render=_render)


def register(app: typer.Typer) -> None:
    app.command("status")(status)
