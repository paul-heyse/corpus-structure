"""CLI adapter for the common pinned contribution inspection service."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from pydantic import JsonValue, RootModel

from corpus_structure.cli.output import JsonOpt, emit, state

app = typer.Typer(help="Inspect independent private contributions and operation outcomes.")


@app.command("list")
def contributions(
    ctx: typer.Context,
    run: Annotated[int, typer.Option()],
    source_view: int | None = None,
    selected_task_id: int | None = None,
    method: str | None = None,
    operation: str | None = None,
    operation_version: str | None = None,
    contribution_id: str | None = None,
    occurrence_id: str | None = None,
    kind: str | None = None,
    include_details: bool = False,
    include_interpretation: bool = False,
    include_scope_coverage: bool = False,
    include_assessment: bool = False,
    include_publication: bool = False,
    include_support: bool = False,
    include_relationships: bool = False,
    relationship_endpoint: str | None = None,
    relationship_direction: str | None = None,
    cursor: str | None = None,
    limit: int = 100,
    max_bytes: int = 8_000_000,
    page_bytes: int = 1_000_000,
    json: JsonOpt = False,
):
    """Read retained products independently of complete record assembly."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.contributions import ContributionRequest, serve_contributions

    with failure_boundary(json):
        request = ContributionRequest.model_validate(
            dict(
                run_id=run,
                source_view_id=source_view,
                selected_task_id=selected_task_id,
                method=method,
                operation_key=operation,
                operation_version=operation_version,
                contribution_id=contribution_id,
                occurrence_id=occurrence_id,
                kind=kind,
                include_details=include_details,
                include_interpretation=include_interpretation,
                include_scope_coverage=include_scope_coverage,
                include_assessment=include_assessment,
                include_publication=include_publication,
                include_support=include_support,
                include_relationships=include_relationships,
                relationship_endpoint=relationship_endpoint,
                relationship_direction=relationship_direction,
                cursor=cursor,
                limit=limit,
                max_bytes=max_bytes,
                page_bytes=page_bytes,
            )
        )
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-contributions", purpose="read"
            ) as engine,
            read_snapshot(engine) as conn,
        ):
            result = serve_contributions(conn, request)
    emit(result, json=json)


@app.command("export")
def export_contributions(
    ctx: typer.Context,
    destination: Path,
    run: Annotated[int, typer.Option()],
    source_view: int | None = None,
    method: str | None = None,
    operation: str | None = None,
    operation_version: str | None = None,
    contribution_id: str | None = None,
    occurrence_id: str | None = None,
    kind: str | None = None,
    include_interpretation: bool = False,
    include_assessment: bool = False,
    include_publication: bool = False,
    include_support: bool = False,
    include_relationships: bool = False,
    relationship_endpoint: str | None = None,
    relationship_direction: str | None = None,
    max_bytes: int = 8_000_000,
    json: JsonOpt = False,
):
    """Detach a bounded selected inventory as JSONL and manifest; private grades excluded."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.contributions import (
        ContributionRequest,
        export_contribution_selection,
    )

    with failure_boundary(json):
        request = ContributionRequest.model_validate(
            dict(
                run_id=run,
                source_view_id=source_view,
                method=method,
                operation_key=operation,
                operation_version=operation_version,
                contribution_id=contribution_id,
                occurrence_id=occurrence_id,
                kind=kind,
                include_interpretation=include_interpretation,
                include_assessment=include_assessment,
                include_publication=include_publication,
                include_support=include_support,
                include_relationships=include_relationships,
                relationship_endpoint=relationship_endpoint,
                relationship_direction=relationship_direction,
                max_bytes=max_bytes,
            )
        )
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-contributions-export", purpose="read"
            ) as engine,
            read_snapshot(engine) as conn,
        ):
            manifest = export_contribution_selection(conn, request, destination)
    emit(RootModel[dict[str, JsonValue]].model_validate(manifest), json=json)


def register(root: typer.Typer):
    root.add_typer(app, name="contributions")
