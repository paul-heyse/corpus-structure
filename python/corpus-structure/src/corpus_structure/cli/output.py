"""What every `ci` command shares: the process state, the `--json` option and result emission.

With `--json`, stdout carries only the result model's `model_dump_json()`, the same shape the query
API and the MCP tools return; otherwise Rich renders it. Diagnostics go to stderr. Consoles are made
per call, so a test runner's stream swap and its `COLUMNS` reach them.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console, RenderableType
from rich.pretty import Pretty
from rich.table import Table
from rich.text import Text

from corpus_structure._diagnostic_capture import safe_text as safe_text
from corpus_structure.settings import Settings, SettingsReport, settings_report

JsonOpt = Annotated[bool, typer.Option("--json", help="Write the result as JSON to stdout.")]


@dataclass
class CliState:
    """`ctx.obj`: a settings factory, called at most once, only by a command that needs settings."""

    settings_factory: Callable[[], Settings] = Settings
    test_args: tuple[str, ...] = ()
    _settings: Settings | None = field(default=None, init=False, repr=False)

    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = self.settings_factory()
        return self._settings


def state(ctx: typer.Context) -> CliState:
    obj = ctx.find_root().obj
    if not isinstance(obj, CliState):
        raise RuntimeError("ci: the root callback did not set the CLI state")
    return obj


def _discard_shutdown_output(descriptor: int) -> None:
    # A failed buffered flush is retried during interpreter shutdown.
    with suppress(OSError):
        fd = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(fd, descriptor)
        finally:
            os.close(fd)


def _undelivered(exit_code: int) -> None:
    if sys.stdout is sys.__stdout__:
        _discard_shutdown_output(1)
    message = "ci: stdout closed before report delivery completed\n"
    if sys.stderr is sys.__stderr__:
        try:
            os.write(2, message.encode())
        except OSError:
            _discard_shutdown_output(2)
    else:
        with suppress(OSError):
            sys.stderr.write(message)
            sys.stderr.flush()
    raise typer.Exit(exit_code or 74)


class _ReportConsole(Console):
    def __init__(self, exit_code: int) -> None:
        super().__init__()
        self.exit_code = exit_code

    def on_broken_pipe(self) -> None:
        _undelivered(self.exit_code)


class _DiagnosticConsole(Console):
    def on_broken_pipe(self) -> None:
        self.quiet = True
        if sys.stderr is sys.__stderr__:
            _discard_shutdown_output(2)


def stdout_console(*, exit_code: int = 0) -> Console:
    return _ReportConsole(exit_code)


def stderr_console() -> Console:
    return _DiagnosticConsole(stderr=True)


def write_report_text(body: str, *, exit_code: int = 0) -> None:
    try:
        sys.stdout.write(body)
        sys.stdout.flush()
    except BrokenPipeError:
        _undelivered(exit_code)


def write_report_bytes(body: bytes, *, exit_code: int = 0) -> None:
    try:
        stream = typer.get_binary_stream("stdout")
        stream.write(body)
        stream.flush()
    except BrokenPipeError:
        _undelivered(exit_code)


def read_request_bytes(source: str | Path) -> bytes:
    limit = 8 * 1024 * 1024
    if str(source) == "-":
        data = typer.get_binary_stream("stdin").read(limit + 1)
    else:
        with Path(source).open("rb") as stream:
            data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("request input exceeds the 8 MiB limit")
    return data


def emit[Report: BaseModel](
    result: Report,
    *,
    json: bool,
    render: Callable[[Report], RenderableType] | None = None,
    exit_code: int = 0,
) -> None:
    """Deliver the typed JSON result or its human projection."""
    if json:
        write_report_text(result.model_dump_json() + "\n", exit_code=exit_code)
        return
    renderable = render(result) if render else Pretty(result.model_dump(mode="json"))
    stdout_console(exit_code=exit_code).print(renderable)


def report_fields(*fields: tuple[str, object]) -> Table:
    """Render a short report with literal values and stable labels."""
    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold")
    table.add_column(overflow="fold")
    for label, value in fields:
        table.add_row(label, Text(safe_text(str(value))))
    return table


def cli_settings_report(settings: Settings) -> SettingsReport:
    report = settings_report(settings, os.environ)
    return report.model_copy(
        update={
            "resolved": {name: safe_text(value) for name, value in report.resolved.items()},
            "unknown_env": tuple(safe_text(name) for name in report.unknown_env),
        }
    )


def diagnostic(value: str) -> None:
    try:
        stderr_console().print(safe_text(value), markup=False, highlight=False)
    except OSError:
        if sys.stderr is sys.__stderr__:
            _discard_shutdown_output(2)
