"""Inspect retained native rich-cell addresses without conversion or recognition."""

import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

with (
    open_runtime_engine(Settings(), "m1-retained-cell-shape", purpose="read") as engine,
    read_snapshot(engine) as conn,
):
    run = table("ops.run")
    release = conn.scalar(select(run.c.release_id).where(run.c.id == 10))
    view = BoundReader(conn, 10, open_release(conn, release), analysis=False).source_view(21)
    node = next(n for n in view.items if n["self_ref"] == "#/tables/0")
    rows = []
    for index in (0, 7, 8, 9, 10, 11):
        pieces = [p for p in view.pieces if p.get("cell_index") == index]
        rows.append(dict(
            index=index, cell=node["data"]["table_cells"][index],
            pieces=[dict(p, projected_text=view.text[p["start"]:p["end"]]) for p in pieces],
            native_items=[n for n in view.items if n["self_ref"] in {
                p.get("item_ref") for p in pieces
            }],
        ))
result = dict(run_id=10, source_view_id=21, cells=rows)
with Path(__file__).with_name("cell-shape.json").open("xb") as stream:
    stream.write(canonical_bytes(result))
print(json.dumps(result))
