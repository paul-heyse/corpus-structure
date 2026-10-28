"""What every `ci` command shares: the process state, the `--json` option and result emission.

With `--json`, stdout carries only the result model's `model_dump_json()`, the same shape the query
API and the MCP tools return; otherwise Rich renders it. Diagnostics go to stderr. Consoles are made
per call, so a test runner's stream swap and its `COLUMNS` reach them.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated

import typer
from pydantic import BaseModel
from rich.console import Console, RenderableType
from rich.pretty import Pretty

from corpus_structure.settings import Settings

JsonOpt = Annotated[bool, typer.Option("--json", help="Write the result as JSON to stdout.")]


@dataclass
class CliState:
    """`ctx.obj`: a settings factory, called at most once, only by a command that needs settings."""

    settings_factory: Callable[[], Settings] = Settings
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
