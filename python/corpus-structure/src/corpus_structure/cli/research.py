"""Read-only pinned research comparisons."""

from __future__ import annotations

from typing import Annotated

import typer

from corpus_structure.cli.output import JsonOpt, emit, state

app = typer.Typer(help="Compare explicitly pinned research inputs.", no_args_is_help=True)


@app.command("compare-exclusions")
def compare_exclusions(
    ctx: typer.Context,
    before_run: Annotated[int, typer.Option()],
    after_run: Annotated[int, typer.Option()],
    limit: int = 100,
    max_rows: int = 1000,
    max_bytes: int = 1024**2,
    retain: bool = False,
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.managed import result_store
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.research import comparison_delivery

    with (
        failure_boundary(json),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-research", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        report = comparison_delivery(
            conn,
            before_run,
            after_run,
            limit=limit,
            max_rows=max_rows,
            max_bytes=max_bytes,
            store=result_store(ctx) if retain else None,
        )
    emit(report, json=json)


def register(root):
    root.add_typer(app, name="research")
