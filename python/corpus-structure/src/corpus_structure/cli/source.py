"""Explicit source-product inspection over one read snapshot."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import typer

from corpus_structure.cli.output import JsonOpt, emit, state

app = typer.Typer(help="Inspect pinned source products and transformation custody.", no_args_is_help=True)


def _read(ctx: typer.Context, **values):
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.source import SourceRequest, inspect_source
    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.operations import OperationConflict
    from sqlalchemy.exc import NoResultFound
    with failure_boundary(True, expected=(ValueError, OperationConflict, NoResultFound)):
        with open_runtime_engine(state(ctx).settings(), application_name="ci-source", purpose="read") as engine, read_snapshot(engine) as conn:
            return inspect_source(conn, SourceRequest(**values))


@app.command("products")
def products(ctx: typer.Context, run: int, rendition: int, producing_task: int | None = None, json: JsonOpt = False):
    emit(_read(ctx, run_id=run, rendition_id=rendition, producing_task_id=producing_task), json=json)


@app.command("inspect")
def inspect(ctx: typer.Context, run: int, rendition: int, representation: str = "canonical", start: int = 0, end: int | None = None, category: str | None = None, relationship: str | None = None, producing_task: int | None = None, limit: int = 1000, json: JsonOpt = False):
    emit(_read(ctx, run_id=run, rendition_id=rendition, producing_task_id=producing_task, view="relationships" if relationship else "components", representation_id=representation, start=start, end=end, category=category, relationship_id=relationship, limit=limit), json=json)


@app.command("trace")
def trace(ctx: typer.Context, run: int, rendition: int, start: int, end: int, representation: str = "canonical", producing_task: int | None = None, exact: bool = False, limit: int = 1000, json: JsonOpt = False):
    emit(_read(ctx, run_id=run, rendition_id=rendition, producing_task_id=producing_task, view="trace", representation_id=representation, start=start, end=end, require_exact=exact, limit=limit), json=json)


@app.command("export")
def export(ctx: typer.Context, run: int, rendition: int, output: Path, representation: str = "canonical", producing_task: int | None = None, format: Literal["jsonl", "parquet"] = "jsonl"):
    import json
    import pyarrow as pa
    import pyarrow.parquet as pq
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.source import SourceRequest, inspect_source
    if output.exists():
        raise typer.BadParameter("output already exists")
    from corpus_structure.semantic.metadata import table
    from corpus_structure.schema.interchange import _sql_arrow
    components = table("kb.parsing_component")
    schema = pa.schema([pa.field(c.name, _sql_arrow(c.type), nullable=bool(c.nullable)) for c in components.columns])
    with open_runtime_engine(state(ctx).settings(), application_name="ci-source-export", purpose="read") as engine, read_snapshot(engine) as conn:
        header = inspect_source(conn, SourceRequest(run_id=run,rendition_id=rendition,producing_task_id=producing_task))
        if header.outcome == "unavailable":
            raise typer.BadParameter(header.diagnostics[0])
        schema = schema.with_metadata({b"source_selection":header.model_dump_json().encode()})
        from corpus_structure.semantic.metadata import table
        from sqlalchemy import select
        components=table("kb.parsing_component")
        stream=conn.execute(select(components).where(components.c.task_id==header.producing_task_id,components.c.representation_id==representation).order_by(components.c.ordinal).execution_options(yield_per=1000))
        temporary = output.with_name(output.name + ".partial")
        with temporary.open("xb") as destination:
            writer=pq.ParquetWriter(destination,schema) if format=="parquet" else None
            try:
                for partition in stream.mappings().partitions(1000):
                    rows=[{name:row[name] for name in schema.names} for row in partition]
                    if writer is not None:
                        writer.write_batch(pa.RecordBatch.from_pylist(rows,schema=schema))
                    else:
                        for row in rows: destination.write((json.dumps({"selection":header.model_dump(mode="json"),"component":row})+"\n").encode())
            finally:
                if writer is not None: writer.close()
        import os
        os.link(temporary, output)
        temporary.unlink()


def register(root: typer.Typer):
    root.add_typer(app,name="source")
