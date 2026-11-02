"""Pinned PDF source inspection shared with MCP; historical HTML requests are retired."""

from __future__ import annotations

import json as jsonlib
from pathlib import Path
from typing import Annotated, Literal

import typer
from pydantic import BaseModel, JsonValue, RootModel

from corpus_structure.cli.output import JsonOpt, emit, state
from corpus_structure.core.db.lifetime import BorrowerCancellation
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
        "artifact",
    ] = "items",
    occurrence: str | None = None,
    artifact_digest: str | None = None,
    collection: Literal["inputs", "coverage", "relations", "mapping_reports"] | None = None,
    cursor: str | None = None,
    limit: int = 100,
    json: JsonOpt = False,
):
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source

    cancellation = BorrowerCancellation()
    with (
        failure_boundary(json, expected=(ValueError,)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-source", purpose="read"
        ) as engine,
        read_snapshot(engine, cancellation=cancellation) as conn,
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
                    artifact_digest=artifact_digest,
                    collection=collection,
                    cursor=cursor,
                    limit=limit,
                ),
                cancellation=cancellation,
            ),
            json=json,
        )


def register(root: typer.Typer):
    root.add_typer(app, name="source")


@app.command("native-export")
def native_export(
    ctx: typer.Context,
    run: Annotated[int, typer.Option()],
    producing_task: Annotated[int, typer.Option()],
    product: Annotated[str, typer.Option()],
    digest: Annotated[str, typer.Option()],
    output: Annotated[Path, typer.Option()],
    section: str | None = None,
    membership: Literal["direct", "descendants"] | None = None,
    format: NativeExportFormat = "parquet",
):
    """Export pinned projections or complete native Docling JSON without inference."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.native_source import NativeSourceRequest, export_native_source

    cancellation = BorrowerCancellation()
    if format == "selected-source-v1":
        from corpus_structure.serve.selected_source import export_selected_native_source

        with failure_boundary(True, expected=(ValueError, FileExistsError)):
            receipt = export_selected_native_source(
                NativeSourceRequest(
                    run_id=run,
                    task_id=producing_task,
                    product_key=product,
                    content_digest=digest,
                    section_pointer=section,
                    membership=membership,
                ),
                output,
                state(ctx).settings(),
                cancellation=cancellation,
            )
            emit(receipt, json=True)
        return
    from tempfile import TemporaryDirectory

    from corpus_structure.serve.native_source import _publish_native_export

    with failure_boundary(True, expected=(ValueError, FileExistsError)):
        if output.exists():
            raise FileExistsError(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".pdf-export-snapshot-", dir=output.parent) as directory:
            staged = Path(directory) / output.name
            with (
                open_runtime_engine(
                    state(ctx).settings(), application_name="ci-native-export", purpose="read"
                ) as engine,
                read_snapshot(engine, cancellation=cancellation) as conn,
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
                    staged,
                    format=format,
                    cancellation=cancellation,
                )
            _publish_native_export(staged, output, cancellation=cancellation)


@app.command("native-products")
def native_products(
    ctx: typer.Context,
    run: int,
    observations: bool = typer.Option(False, help="List retained recognition observation pins."),
    task: int | None = typer.Option(None, help="Exact finished source task for observations."),
    cursor: str | None = None,
    limit: int = typer.Option(100, min=1, max=1000),
    json: JsonOpt = False,
):
    """List native pins, or a bounded recognition catalog from one finished source task."""
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
        if observations:
            from corpus_structure.semantic.pdf_storage import (
                PdfObservationListRequest,
                read_pdf_observations,
            )

            if task is None:
                raise ValueError("--observations requires --task with a finished source task")
            emit(
                read_pdf_observations(
                    conn,
                    PdfObservationListRequest(run_id=run, task_id=task, cursor=cursor, limit=limit),
                ),
                json=json,
            )
            return
        if task is not None or cursor is not None or limit != 100:
            raise ValueError("observation catalog paging requires --observations")
        context = pdf_context_for_run(conn, run)
        context.execution.require_operation("read_native_source")
        context.boundary.validate_json("PdfNativeRunRequest", jsonlib.dumps(dict(run_id=run)))
        products, tasks = map(table, ("ops.pdf_selected_product", "ops.task"))
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
                tasks.c.run_id.label("origin_run"),
            )
            .join(tasks, tasks.c.id == products.c.task_id)
            .where(or_(tasks.c.run_id == run, pins.exists()))
            .order_by(products.c.task_id, products.c.product_key)
        )
        catalog = list(conn.execute(query).mappings())
        from corpus_structure.semantic.pdf_record_reader import published_record_reader
        from corpus_structure.semantic.pdf_storage import _record_product_identity
        from corpus_structure.semantic.product_reference import ProductReference
        from corpus_structure.semantic.releases import open_release
        from corpus_structure.serve.native_source import _published_native_header

        if context.release_id is None:
            raise ValueError("native catalog requires its archived run release")
        projection_context = open_release(conn, context.release_id)
        rows = []
        for row in catalog:
            pin = ProductReference(row["task_id"], row["product_key"], row["content_digest"])
            reader = published_record_reader(conn, pin, projection_context=projection_context)
            if reader is None:
                raise ValueError("catalog publication pin is unavailable")
            _record_product_identity(
                conn, pin.task_id, pin.product_key, pin.content_digest, reader
            )
            header = _published_native_header(reader, row["origin_run"], runtime=True)
            health, report, release_id = header.health, header.runtime_report, header.release_id
            rows.append(
                NativeProductReport(
                    task_id=pin.task_id,
                    product_key=pin.product_key,
                    content_digest=pin.content_digest,
                    release_id=release_id,
                    health=health,
                    runtime_report=report,
                )
            )
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


@app.command("companion-export")
def companion_export(
    ctx: typer.Context,
    run: Annotated[int, typer.Option()],
    producing_task: Annotated[int, typer.Option()],
    product: Annotated[str, typer.Option()],
    digest: Annotated[str, typer.Option()],
    project: Annotated[str, typer.Option()],
    selection_release: Annotated[str, typer.Option()],
    output: Annotated[Path, typer.Option()],
    family: Annotated[list[str] | None, typer.Option("--family")] = None,
    json: JsonOpt = False,
):
    """Export detached typed companion families from one exact published pin."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.companion_export import (
        CompanionExportRequest,
        PublishedSourcePin,
        export_companion_parquet,
    )

    with failure_boundary(json, expected=(ValueError, FileExistsError)):
        values: dict = dict(
            pin=PublishedSourcePin(
                project_id=project,
                selection_release_id=selection_release,
                run_id=run,
                task_id=producing_task,
                product_key=product,
                content_digest=digest,
            ),
            destination=output,
        )
        if family:
            values["families"] = tuple(family)
        request = CompanionExportRequest.model_validate(values)
        emit(export_companion_parquet(request, state(ctx).settings()), json=json)


@app.command("companion-inventory")
def companion_inventory(manifest: Path, json: JsonOpt = False):
    """Inventory only verified manifest-listed files, without a database session."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.companion_export import inventory_companion_export

    with failure_boundary(json, expected=(ValueError, OSError)):
        emit(RootModel(inventory_companion_export(manifest)), json=json)


@app.command("companion-compare")
def companion_compare(left: Path, right: Path, json: JsonOpt = False):
    """Compare compatible detached projections while preserving duplicates."""
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.serve.companion_export import compare_companion_exports

    with failure_boundary(json, expected=(ValueError, OSError)):
        emit(RootModel(compare_companion_exports(left, right)), json=json)
