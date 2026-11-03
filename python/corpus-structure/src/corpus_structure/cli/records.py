"""Thin CLI journeys over the pinned common source-record reader."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import typer

from corpus_structure.cli.output import JsonOpt, emit, state

app = typer.Typer(
    help="Inspect pinned released source records and their evidence.", no_args_is_help=True
)


@app.command("list")
def records(
    ctx: typer.Context,
    run: Annotated[int, typer.Option()],
    project: str | None = None,
    source_view: Annotated[list[int] | None, typer.Option("--source-view")] = None,
    family: str | None = None,
    standing: str | None = None,
    record: str | None = None,
    interpretation: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    page_bytes: int = 1024**2,
    json: JsonOpt = False,
):
    """List records, or inspect one identity with --record and --interpretation.

    Paging completion describes the returned population, never source coverage.
    """
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.record_results import RecordRequest, serve_record_results

    with (
        failure_boundary(json),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-records", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        result = serve_record_results(
            conn,
            RecordRequest(
                run_id=run,
                project_id=project,
                source_view_ids=tuple(source_view) if source_view is not None else None,
                family=family,
                standing=standing,
                record_id=record,
                interpretation_id=interpretation,
                cursor=cursor,
                limit=limit,
                page_bytes=page_bytes,
            ),
        )
    emit(result, json=json)


@app.command("export")
def export_records(
    ctx: typer.Context,
    run: Annotated[int, typer.Option()],
    out: Annotated[Path, typer.Option()],
    project: str | None = None,
    format: Literal["jsonl", "parquet"] = "parquet",
    capture_mode: Literal["resident", "spooled"] | None = None,
    json: JsonOpt = False,
):
    """Export all 18 record relations with the same pinned captured semantic packet."""
    from corpus_structure.cli.export import export

    return export(
        ctx,
        out=out,
        format=format,
        capture_mode=capture_mode,
        run=str(run),
        project=project,
        json=json,
        include_records=True,
    )


def register(root: typer.Typer):
    root.add_typer(app, name="records")
