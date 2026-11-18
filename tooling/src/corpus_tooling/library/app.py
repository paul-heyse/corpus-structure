"""The `library` group: its target options and the explicit list of its commands.

Each command module exports `register(group: typer.Typer) -> None`; adding a command adds one
entry to `REGISTRATIONS`. Every registered command runs under `EnvelopeCommand`, which delivers
a `ToolFailure` as exit 3 with a failed envelope.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Annotated

import typer

from corpus_tooling.library import baseline, metadata, overview, selection
from corpus_tooling.library.context import LibraryState
from corpus_tooling.output import envelope_commands

Registration = Callable[[typer.Typer], None]

# One line per command; the order is the order `--help` lists them.
REGISTRATIONS: Sequence[Registration] = [
    baseline.register,
    selection.register,
    metadata.register,
    overview.register,
]


def library(
    ctx: typer.Context,
    project: Annotated[
        Path | None,
        typer.Option(
            "--project",
            exists=True,
            file_okay=False,
            help="The uv project directory (default: the nearest ancestor holding uv.lock).",
        ),
    ] = None,
    python: Annotated[
        Path | None,
        typer.Option(
            "--python",
            exists=True,
            help="The target environment or its interpreter (default: the project's .venv).",
        ),
    ] = None,
) -> None:
    """Read-only facts about third-party libraries for library-led discovery."""
    ctx.obj = LibraryState(cwd=Path.cwd(), project=project, python=python)


def make_library_app(registrations: Sequence[Registration] = REGISTRATIONS) -> typer.Typer:
    group = typer.Typer(no_args_is_help=True)
    group.callback()(library)
    for register in registrations:
        register(group)
    envelope_commands(group)
    return group


app = make_library_app()
