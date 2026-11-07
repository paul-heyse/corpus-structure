"""What every `ci` command shares: the process state, the `--json` option and result emission.

With `--json`, stdout carries only the result model's `model_dump_json()`, the same shape the query
API and the MCP tools return; otherwise Rich renders it. Diagnostics go to stderr. Consoles are made
per call, so a test runner's stream swap and its `COLUMNS` reach them.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console, RenderableType
from rich.pretty import Pretty

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


def stdout_console() -> Console:
    return Console()


def stderr_console() -> Console:
    return Console(stderr=True)


def emit(
    result: BaseModel,
    *,
    json: bool,
    render: Callable[[BaseModel], RenderableType] | None = None,
) -> None:
    """Write `result`: its JSON to stdout with `json`, else its Rich rendering."""
    if json:
        sys.stdout.write(result.model_dump_json() + "\n")
        return
    renderable = render(result) if render else Pretty(result.model_dump(mode="json"))
    stdout_console().print(renderable)


_TERMINAL = re.compile(r"\x1b(?:\][^\x07\x1b]*(?:\x07|\x1b\\)|\[[0-?]*[ -/]*[@-~])")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_CREDENTIAL = re.compile(
    r"(://[^:/@\s]+:)[^@/\s]+(?=@)|"
    r"(?i:(password|token|api[_-]?key)\s*=\s*)(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|[^\s&]+)"
)


def safe_text(value: str) -> str:
    """Remove terminal controls and redact credentials from complete diagnostic text."""
    value = _CONTROL.sub("", _TERMINAL.sub("", value))
    for key, secret in os.environ.items():
        if secret and (
            key == "PGPASSWORD"
            or (
                key.startswith("CORPUS_")
                and any(part in key for part in ("PASSWORD", "TOKEN", "API_KEY"))
            )
        ):
            value = value.replace(secret, "**********")
    return _CREDENTIAL.sub(lambda match: (match[1] or f"{match[2]}=") + "**********", value)


def cli_settings_report(settings: Settings) -> SettingsReport:
    report = settings_report(settings, os.environ)
    return report.model_copy(
        update={
            "resolved": {name: safe_text(value) for name, value in report.resolved.items()},
            "unknown_env": tuple(safe_text(name) for name in report.unknown_env),
        }
    )


def diagnostic(value: str) -> None:
    stderr_console().print(safe_text(value), markup=False, highlight=False)
