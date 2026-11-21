"""Read Chandra diagnostics and retained dispatch results."""

from pathlib import Path

import typer

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, read_continuation, state


def visual_route(
    ctx: typer.Context,
    demand: str,
    project: str = typer.Option(...),
    first: int = 1,
    limit: int = 32,
    continuation: Path | None = None,
    json: JsonOpt = False,
) -> None:
    """Assess selected visual products under their explicit native demand cut."""
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.visual_routing import read_demand_visual_routes

    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-visual-route", purpose="read"
        ) as engine,
        engine.begin() as conn,
    ):
        report = read_demand_visual_routes(
            conn,
            demand,
            project_id=project,
            first=first,
            limit=limit,
            continuation=read_continuation(continuation),
        )
    from corpus_structure.cli.demands import DemandSnapshot, _emit_demand

    _emit_demand(DemandSnapshot.model_validate(report), json=json)
