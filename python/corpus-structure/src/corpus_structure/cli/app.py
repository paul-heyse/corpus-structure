"""The `ci` Typer app (D8 §4; interfaces note §3).

The root callback stores a settings factory in `ctx.obj`, so `--help` and completion never build
settings or touch the database. `--json` is a per-command option (`ci status --json`).
"""

from __future__ import annotations

import sys

import typer

from corpus_structure.cli import REGISTRY
from corpus_structure.cli.output import CliState

app = typer.Typer(
    name="ci",
    help="corpus-structure: build and query a structured representation of a corpus.",
    no_args_is_help=True,
    add_completion=True,
    pretty_exceptions_show_locals=False,
)


@app.callback()
def root(ctx: typer.Context) -> None:
    """corpus-structure: build and query a structured representation of a corpus."""
    if ctx.obj is None:
        ctx.obj = CliState()


for register in REGISTRY:
    register(app)


def main() -> None:
    arguments = sys.argv[1:]
    if arguments[:1] == ["test"] and "--" in arguments:
        boundary = arguments.index("--")
        app(args=arguments[:boundary], obj=CliState(test_args=tuple(arguments[boundary + 1 :])))
    else:
        app()
