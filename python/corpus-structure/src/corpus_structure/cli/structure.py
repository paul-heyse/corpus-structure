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
    include_publication: bool = False,
    include_support: bool = False,
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
                include_publication=include_publication,
                include_support=include_support,
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


@app.command("dossier-page")
def dossier_page(
    ctx: typer.Context,
    run: Annotated[int, typer.Option()],
    task: Annotated[int, typer.Option()],
    cut: int | None = None,
    limit: int = 20,
    max_bytes: int = 1_000_000,
    continuation: str | None = None,
    json: JsonOpt = False,
):
    """Page an immutable dossier's selected representation and exact citations."""
    import json as json_module

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.structural_products import (
        DossierRepresentationRequest,
        serve_dossier_representation,
    )

    with failure_boundary(json):
        request = DossierRepresentationRequest.model_validate(
            dict(
                run_id=run,
                task_id=task,
                cut_id=cut,
                limit=limit,
                max_bytes=max_bytes,
                continuation=json_module.loads(continuation) if continuation else None,
            )
        )
        with (
            open_runtime_engine(state(ctx).settings(), "ci-dossier", purpose="read") as engine,
            read_snapshot(engine) as conn,
        ):
            result = serve_dossier_representation(conn, request)
    emit(result, json=json)


@app.command("gap")
def structural_gap(
    ctx: typer.Context,
    report: str,
    run: Annotated[int, typer.Option()],
    task: Annotated[int, typer.Option()],
    cut: int | None = None,
    source_view: int | None = None,
    scope: str | None = None,
    occurrence: str | None = None,
    operation: str | None = None,
    binding_run: int | None = None,
    binding_cut: int | None = None,
    binding_task: int | None = None,
    limit: int = 20,
    max_bytes: int = 1_000_000,
    cursor: str | None = None,
    json: JsonOpt = False,
):
    """Inspect one selected structural gap report and its producer coverage."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.structural_gaps import GapRequest, serve_structural_gap

    with failure_boundary(json):
        request = GapRequest.model_validate(
            dict(
                report=report,
                run_id=run,
                task_id=task,
                cut_id=cut,
                source_view_id=source_view,
                scope=scope,
                occurrence_id=occurrence,
                operation_key=operation,
                limit=limit,
                max_bytes=max_bytes,
                cursor=cursor,
                binding_task=dict(
                    run_id=binding_run or run, task_id=binding_task, cut_id=binding_cut
                )
                if any(value is not None for value in (binding_run, binding_cut, binding_task))
                else None,
            )
        )
        with (
            open_runtime_engine(
                state(ctx).settings(), "ci-structural-gap", purpose="read"
            ) as engine,
            read_snapshot(engine) as conn,
        ):
            result = serve_structural_gap(conn, request)
    emit(result, json=json)
