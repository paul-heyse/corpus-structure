"""Inspect immutable cross-source structural proposals."""

from typing import Annotated

import typer

from corpus_structure.cli.output import JsonOpt, emit, state

app = typer.Typer(help="Inspect cross-source definitions, comparisons and dossiers.")


@app.command("list")
def structures(
    ctx: typer.Context,
    run: Annotated[int, typer.Option()],
    kind: str | None = None,
    cut: int | None = None,
    after_task: int = 0,
    limit: int = 20,
    max_bytes: int = 1_000_000,
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.structural_products import (
        StructuralRequest,
        serve_structural_products,
    )

    with failure_boundary(json):
        request = StructuralRequest.model_validate(
            dict(
                run_id=run,
                cut_id=cut,
                kind=kind,
                after_task_id=after_task,
                limit=limit,
                max_bytes=max_bytes,
            )
        )
        with (
            open_runtime_engine(state(ctx).settings(), "ci-structure", purpose="read") as engine,
            read_snapshot(engine) as conn,
        ):
            result = serve_structural_products(conn, request)
    emit(result, json=json)


def register(root: typer.Typer):
    root.add_typer(app, name="structure")
