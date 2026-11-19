"""Process-local cache diagnostics."""

import typer

from .output import JsonOpt, emit, state

app = typer.Typer(help="Inspect process-local reuse and retention.", no_args_is_help=True)


@app.command("stats")
def stats(ctx: typer.Context, json: JsonOpt = False) -> None:
    """Report this invocation's counters and configured cache bounds."""
    from corpus_structure.caches import snapshot

    state(ctx).settings()
    emit(snapshot(owner="ci"), json=json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="cache")
