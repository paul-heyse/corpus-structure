"""Read-only pinned research comparisons."""

from __future__ import annotations

from typing import Annotated

import typer

from corpus_structure.cli.output import JsonOpt, emit, state

app = typer.Typer(help="Compare explicitly pinned research inputs.", no_args_is_help=True)


@app.command(
    "compare-exclusions",
    epilog=(
        "Example: ci research compare-exclusions --before-run 10 "
        "--after-run 11 --json\n\nDomain contract: [domain "
        "reader](docs/design/D8-agent-and-query-interfaces.md)"
    ),
)
def compare_exclusions(
    ctx: typer.Context,
    before_run: Annotated[
        int, typer.Option(help="Pinned source run ID.", rich_help_panel="Inputs")
    ],
    after_run: Annotated[int, typer.Option(help="Pinned source run ID.", rich_help_panel="Inputs")],
    limit: Annotated[
        int,
        typer.Option(
            min=1, max=1000, help="Maximum changed exclusion entries.", rich_help_panel="Delivery"
        ),
    ] = 100,
    max_rows: Annotated[
        int,
        typer.Option(
            min=1, max=10000, help="Maximum examined rows per input.", rich_help_panel="Inputs"
        ),
    ] = 1000,
    max_bytes: Annotated[
        int,
        typer.Option(
            min=1,
            max=8 * 1024**2,
            help="Byte bound for captures and response.",
            rich_help_panel="Delivery",
        ),
    ] = 1024**2,
    retain: Annotated[
        bool,
        typer.Option(
            "--retain/--no-retain",
            help="Publish the comparison in managed storage.",
            rich_help_panel="Delivery",
        ),
    ] = False,
    json: JsonOpt = False,
):
    """Compare exclusions in two pinned runs; optionally retain the bounded read result."""
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
