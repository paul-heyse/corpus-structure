"""Pinned PDF source inspection shared with MCP; historical HTML requests are retired."""

from __future__ import annotations

import json as jsonlib
from pathlib import Path
from typing import Literal

import typer
from pydantic import BaseModel, JsonValue, RootModel

from corpus_structure.cli.output import JsonOpt, emit, state
from corpus_structure.serve.native_source import NativeExportFormat

app = typer.Typer(help="Inspect pinned PDF sources and integration custody.", no_args_is_help=True)


class NativeProductReport(BaseModel):
    task_id: int
    product_key: str
    content_digest: str
    release_id: str
    health: dict[str, JsonValue]
    runtime_report: dict[str, JsonValue] | None


@app.command("inspect")
def inspect(
    ctx: typer.Context,
    run: int,
    producing_task: int = typer.Option(...),
    product: str = typer.Option(...),
    native_digest: str = typer.Option(...),
    pointer: str | None = None,
    section: str | None = None,
    membership: Literal["direct", "descendants"] | None = None,
    cell: int | None = None,
    native_view: Literal[
        "products",
        "items",
        "sections",
        "item",
        "formula",
        "cell",
        "regions",
        "trace",
        "companion",
        "manifest",
    ] = "items",
    occurrence: str | None = None,
    collection: Literal["inputs", "coverage", "relations"] | None = None,
    cursor: str | None = None,
    limit: int = 100,
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source

    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-source", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        emit(
            inspect_native_source(
                conn,
                NativeSourceRequest(
                    run_id=run,
                    task_id=producing_task,
                    product_key=product,
                    content_digest=native_digest,
                    view=native_view,
                    pointer=pointer,
                    section_pointer=section,
                    membership=membership,
                    cell_index=cell,
                    occurrence_id=occurrence,
                    collection=collection,
                    cursor=cursor,
                    limit=limit,
                ),
            ),
            json=json,
        )


def register(root: typer.Typer):
    root.add_typer(app, name="source")


@app.command("native-export")
def native_export(
    ctx: typer.Context,
    run: int,
    producing_task: int,
    product: str,
    digest: str,
    output: Path,
    section: str | None = None,
    membership: Literal["direct", "descendants"] | None = None,
    format: NativeExportFormat = "parquet",
):
    """Export pinned projections or complete native Docling JSON without inference."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.native_source import NativeSourceRequest, export_native_source

    with (
        failure_boundary(True, expected=(ValueError, FileExistsError)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-native-export", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        export_native_source(
            conn,
            NativeSourceRequest(
                run_id=run,
                task_id=producing_task,
                product_key=product,
                content_digest=digest,
                section_pointer=section,
                membership=membership,
                limit=1000,
            ),
            output,
            format=format,
        )


@app.command("native-products")
def native_products(ctx: typer.Context, run: int, json: JsonOpt = False):
    """List immutable native source pins produced or selected by a run."""
    from sqlalchemy import or_, select

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_run
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine

    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-native-products", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        context = pdf_context_for_run(conn, run)
        context.execution.require_operation("read_native_source")
        context.boundary.validate_json("PdfNativeRunRequest", jsonlib.dumps(dict(run_id=run)))
        products, tasks = map(table, ("ops.pdf_selected_product", "ops.task"))
        runtime = table("kb.native_document_runtime")
        from corpus_structure.semantic.pdf_storage import selected_native_ancestry

        ancestors = selected_native_ancestry(run)
        pins = select(ancestors.c.task_id).where(
            ancestors.c.task_id == products.c.task_id,
            ancestors.c.product_key == products.c.product_key,
            ancestors.c.content_digest == products.c.content_digest,
        )
        query = (
            select(
                products.c.task_id,
                products.c.product_key,
                products.c.content_digest,
                products.c.release_id,
                products.c.health.op("-")("formula_outcomes").label("health"),
                runtime.c.report.label("runtime_report"),
            )
            .join(tasks, tasks.c.id == products.c.task_id)
            .outerjoin(
                runtime,
                (runtime.c.task_id == products.c.task_id)
                & (runtime.c.product_key == products.c.product_key),
            )
            .where(or_(tasks.c.run_id == run, pins.exists()))
            .order_by(products.c.task_id, products.c.product_key)
        )
        rows = [NativeProductReport.model_validate(row) for row in conn.execute(query).mappings()]
        emit(RootModel[list[NativeProductReport]](rows), json=json)


@app.command("native-request")
def native_request(
    ctx: typer.Context,
    run: int,
    source_view: int,
    demand: Literal[
        "lexical", "structure", "syntax", "interpretation", "symbolic", "assessment", "render"
    ],
    pointer: str | None = None,
    region_index: int | None = None,
    scale: float = 2,
    question: str | None = None,
    predicate: str | None = None,
    seconds: float = 2,
    output: Path | None = None,
    json: JsonOpt = False,
):
    """Execute an explicit native demand through the existing source-ready task lifecycle."""
    from sqlalchemy import select

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.native_requests import request_source_view
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.runtime import open_runtime_engine

    if output is not None and (demand != "render" or output.exists()):
        raise typer.BadParameter("a new --output path is available only for render demands")
    with (
        failure_boundary(json, expected=(ValueError, OperationConflict, FileExistsError)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-native-request", purpose="write"
        ) as engine,
    ):
        result = request_source_view(
            engine,
            source_run_id=run,
            source_view_id=source_view,
            demand=demand,
            pointer=pointer,
            region_index=region_index,
            scale=scale,
            question=question,
            predicate=predicate,
            seconds=seconds,
            code_commit="native-source-cli-v2",
        )
        if result.status == "failed":
            emit(RootModel(result), json=json)
            raise typer.Exit(1)
        if output is not None:
            artifacts = table("kb.source_artifact")
            with engine.connect() as conn:
                value = bytes(
                    conn.execute(
                        select(artifacts.c.content).where(
                            artifacts.c.artifact_digest == result.artifact_digest
                        )
                    ).scalar_one()
                )
            with output.open("xb") as target:
                target.write(value)
        emit(RootModel(result), json=json)


@app.command("views")
def native_views(ctx: typer.Context, run: int, json: JsonOpt = False):
    """List selected native section view IDs and immutable source pins."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_run
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.semantic.source_views import selected_source_views

    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-source-views", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        context = pdf_context_for_run(conn, run)
        context.execution.require_operation("read_source_view")
        context.boundary.validate_json("PdfNativeRunRequest", jsonlib.dumps(dict(run_id=run)))
        emit(RootModel(selected_source_views(conn, run)), json=json)
