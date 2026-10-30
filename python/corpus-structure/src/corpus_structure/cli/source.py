"""Explicit source-product inspection over one read snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import typer

from corpus_structure.cli.output import JsonOpt, emit, state

app = typer.Typer(
    help="Inspect pinned source products and transformation custody.", no_args_is_help=True
)


def _read(ctx: typer.Context, **values):
    from sqlalchemy.exc import NoResultFound

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.source import SourceRequest, inspect_source

    with (
        failure_boundary(True, expected=(ValueError, OperationConflict, NoResultFound)),
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-source", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        return inspect_source(conn, SourceRequest(**values))


@app.command("products")
def products(
    ctx: typer.Context,
    run: int,
    rendition: int,
    producing_task: int | None = None,
    json: JsonOpt = False,
):
    emit(
        _read(ctx, run_id=run, rendition_id=rendition, producing_task_id=producing_task), json=json
    )


@app.command("inspect")
def inspect(
    ctx: typer.Context,
    run: int,
    rendition: int,
    product: str = "source",
    representation: str = "canonical",
    start: int = 0,
    end: int | None = None,
    category: str | None = None,
    relationship: str | None = None,
    producing_task: int | None = None,
    limit: int = 1000,
    json: JsonOpt = False,
):
    emit(
        _read(
            ctx,
            run_id=run,
            rendition_id=rendition,
            producing_task_id=producing_task,
            product_key=product,
            view="relationships" if relationship else "components",
            representation_id=representation,
            start=start,
            end=end,
            category=category,
            relationship_id=relationship,
            limit=limit,
        ),
        json=json,
    )


@app.command("trace")
def trace(
    ctx: typer.Context,
    run: int,
    rendition: int,
    start: int,
    end: int,
    product: str = "source",
    representation: str = "canonical",
    producing_task: int | None = None,
    exact: bool = False,
    limit: int = 1000,
    json: JsonOpt = False,
):
    emit(
        _read(
            ctx,
            run_id=run,
            rendition_id=rendition,
            producing_task_id=producing_task,
            product_key=product,
            view="trace",
            representation_id=representation,
            start=start,
            end=end,
            require_exact=exact,
            limit=limit,
        ),
        json=json,
    )


@app.command("export")
def export(
    ctx: typer.Context,
    run: int,
    rendition: int,
    output: Path,
    product: str = "source",
    representation: str = "canonical",
    producing_task: int | None = None,
    format: Literal["jsonl", "parquet"] = "jsonl",
):
    import json

    import pyarrow as pa
    import pyarrow.parquet as pq

    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.source import SourceRequest, inspect_source

    if output.exists():
        raise typer.BadParameter("output already exists")
    from corpus_structure.schema.interchange import _sql_arrow
    from corpus_structure.semantic.metadata import table

    components = table(
        "kb.parsing_component" if product == "source" else "kb.parsing_layer_component"
    )
    schema = pa.schema(
        [
            pa.field(c.name, _sql_arrow(c.type), nullable=bool(c.nullable))
            for c in components.columns
        ]
    )
    with (
        open_runtime_engine(
            state(ctx).settings(), application_name="ci-source-export", purpose="read"
        ) as engine,
        read_snapshot(engine) as conn,
    ):
        header = inspect_source(
            conn,
            SourceRequest(
                run_id=run,
                rendition_id=rendition,
                producing_task_id=producing_task,
                product_key=product,
            ),
        )
        if header.outcome == "unavailable":
            raise typer.BadParameter(header.diagnostics[0])
        schema = schema.with_metadata({b"source_selection": header.model_dump_json().encode()})
        from sqlalchemy import select

        from corpus_structure.semantic.metadata import table

        inspect_source(
            conn,
            SourceRequest(
                run_id=run,
                rendition_id=rendition,
                producing_task_id=header.producing_task_id,
                product_key=product,
                view="components",
                representation_id=representation,
                start=0,
                end=0,
            ),
        )
        query = select(components).where(
            components.c.task_id == header.producing_task_id,
            components.c.representation_id == representation,
        )
        if product != "source":
            query = query.where(components.c.product_key == product)
        stream = conn.execute(
            query.order_by(components.c.ordinal).execution_options(yield_per=1000)
        )
        temporary = output.with_name(output.name + ".partial")
        with temporary.open("xb") as destination:
            writer = pq.ParquetWriter(destination, schema) if format == "parquet" else None
            try:
                for partition in stream.mappings().partitions(1000):
                    rows = [{name: row[name] for name in schema.names} for row in partition]
                    if writer is not None:
                        writer.write_batch(pa.RecordBatch.from_pylist(rows, schema=schema))
                    else:
                        for row in rows:
                            destination.write(
                                (
                                    json.dumps(
                                        {
                                            "selection": header.model_dump(mode="json"),
                                            "component": row,
                                        }
                                    )
                                    + "\n"
                                ).encode()
                            )
            finally:
                if writer is not None:
                    writer.close()
        import os

        os.link(temporary, output)
        temporary.unlink()


@app.command("request")
def request(
    ctx: typer.Context,
    run: int,
    rendition: int,
    demand: Literal["lexical", "structure", "syntax", "interpretation", "symbolic", "assessment"],
    source_task: int | None = None,
    math_index: int | None = None,
    start: int | None = None,
    end: int | None = None,
    question: str | None = None,
    predicate: str | None = None,
    seconds: float | None = None,
    json: JsonOpt = False,
):
    """Compute an explicitly requested capability in a new fenced operation."""
    from pydantic import RootModel

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.core.provenance import code_commit
    from corpus_structure.methods.math.grammar import PARSE_SECONDS
    from corpus_structure.semantic.operations import OperationConflict
    from corpus_structure.semantic.parsing_products import select_layered_products
    from corpus_structure.semantic.parsing_requests import request_parsing
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine

    settings = state(ctx).settings()
    with failure_boundary(json, expected=(ValueError, OperationConflict)):
        with (
            open_runtime_engine(
                settings, application_name="ci-source-request-input", purpose="read"
            ) as engine,
            read_snapshot(engine) as conn,
        ):
            roots = select_layered_products(
                conn, run_id=run, rendition_id=rendition, kind="source", root_task_id=source_task
            )
            if len(roots) != 1:
                raise ValueError("select one retained source build")
            texts = select_layered_products(
                conn,
                run_id=run,
                rendition_id=rendition,
                kind="text",
                product_key="text",
                root_task_id=roots[0].reference.task_id,
            )
            if len(texts) != 1:
                raise ValueError("select one retained source-bound text product")
            root_ref, text_ref = roots[0].reference, texts[0].reference
        with open_runtime_engine(
            settings, application_name="ci-source-request", purpose="write"
        ) as engine:
            result = request_parsing(
                engine,
                root=root_ref,
                text_product=text_ref,
                demand=demand,
                code_commit=code_commit(),
                math_index=math_index,
                start=start,
                end=end,
                question=question,
                predicate=predicate,
                seconds=PARSE_SECONDS if seconds is None else seconds,
            )
        emit(RootModel(result), json=json)
        if result.status != "source_ready":
            raise typer.Exit(1)


def register(root: typer.Typer):
    root.add_typer(app, name="source")
