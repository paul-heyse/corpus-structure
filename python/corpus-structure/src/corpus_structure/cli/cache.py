"""Process cache inspection."""

import typer

from .output import JsonOpt, emit, state

app = typer.Typer(help="Inspect process reuse and retention.", no_args_is_help=True)


@app.command("stats")
def stats(ctx: typer.Context, json: JsonOpt = False) -> None:
    """Report this invocation's process retention counters."""
    from corpus_structure.caches import snapshot
    from corpus_structure.cli.failures import failure_boundary

    with failure_boundary(json, expected=(ValueError, OSError)):
        state(ctx).settings()
        emit(snapshot(owner="ci"), json=json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="cache")
