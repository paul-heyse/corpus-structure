"""Read deterministic Chandra routing nominations without starting inference."""

import typer

from corpus_structure.cli.failures import failure_boundary
from corpus_structure.cli.output import JsonOpt, emit, state


def visual_route(
    ctx: typer.Context,
    run: int,
    producing_task: int = typer.Option(...),
    product: str = typer.Option(...),
    native_digest: str = typer.Option(...),
    first: int = 1,
    limit: int = 32,
    json: JsonOpt = False,
) -> None:
    """Evaluate a bounded physical-page range of an exact published integrated PDF."""
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.visual_routing import read_visual_routes
    from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-visual-route", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        source = VisualEvidencePin(
            run_id=run, task_id=producing_task, product_key=product, content_digest=native_digest
        )
        report = read_visual_routes(conn, source, first=first, limit=limit)
    emit(report, json=json)
