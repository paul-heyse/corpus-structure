"""Versioned, source-qualified native reads without converter/model initialization."""
from __future__ import annotations

import base64
import json
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic_core import to_jsonable_python
from sqlalchemy import Connection, select


class NativeSourceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    version: Literal[2] = 2
    run_id: int = Field(gt=0)
    task_id: int = Field(gt=0)
    product_key: str = Field(min_length=1)
    content_digest: str = Field(pattern=r'^[0-9a-f]{64}$')
    view: Literal['products','items','sections','item','formula','cell','regions','trace'] = 'items'
    section_pointer: str | None = None
    pointer: str | None = None
    cell_index: int | None = Field(default=None,ge=0)
    cursor: str | None = None
    limit: int = Field(default=100,ge=1,le=1000)

    def selection_digest(self) -> str:
        values = self.model_dump(exclude={'cursor','limit'})
        return sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode()).hexdigest()


class NativeSourceResponse(BaseModel):
    model_config = ConfigDict(frozen=True,extra='forbid')
    version: Literal[2] = 2
    selection: NativeSourceRequest
    release_id: str
    outcome: Literal['available','unavailable'] = 'available'
    health: dict[str,JsonValue]
    rows: list[dict[str,JsonValue]]
    next_cursor: str | None = None


def inspect_native_source(conn: Connection, request: NativeSourceRequest) -> NativeSourceResponse:
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_storage import read_native_items, read_native_regions

    runs,tasks,products,builds = map(table,('ops.run','ops.task','ops.native_document_product','ops.source_build'))
    run = conn.execute(select(runs.c.project_id,runs.c.release_id).where(runs.c.id==request.run_id)).one()
    origin = runs.alias('native_origin_run')
    header = conn.execute(select(products.c.release_id,products.c.health,products.c.content_digest,
        builds.c.artifact_digest,tasks.c.run_id.label('origin_run')).select_from(products.join(tasks,
        tasks.c.id==products.c.task_id).join(origin,origin.c.id==tasks.c.run_id).join(builds,
        builds.c.task_id==products.c.task_id)).where(products.c.task_id==request.task_id,
        products.c.product_key==request.product_key,origin.c.project_id==run.project_id,
        )).one()
    if header.content_digest != request.content_digest:
        raise ValueError('native source product differs from requested pin')
    if header.origin_run != request.run_id:
        # Cross-run reads require an explicitly selected view, never equal text or latest build.
        selected,views = table('ops.run_source_view'),table('kb.source_view')
        chosen = conn.execute(select(views.c.id).join(selected,selected.c.source_view_id==views.c.id).where(
            selected.c.run_id==request.run_id,views.c.native_task_id==request.task_id,
            views.c.native_product_key==request.product_key,views.c.native_content_digest==request.content_digest
        ).limit(1)).first()
        if chosen is None:
            raise ValueError('native source is not selected by the requested run')
    after=-1
    if request.cursor is not None:
        try:
            cursor=json.loads(base64.urlsafe_b64decode(request.cursor))
            if cursor['selection']!=request.selection_digest() or type(cursor['after']) is not int:
                raise ValueError('cursor selection differs')
            after=cursor['after']
        except (KeyError,ValueError,TypeError) as error:
            raise ValueError('invalid native continuation') from error
    pin=dict(task_id=request.task_id,product_key=request.product_key,content_digest=request.content_digest)
    # The qualified storage reader checks the admitted archived schema/contract even for metadata reads.
    rows=read_native_items(conn,**pin,section_pointer=request.section_pointer,
        pointer=request.pointer,after=after,limit=request.limit)
    next_cursor=None
    if request.view=='products':
        rows=[dict(task_id=request.task_id,product_key=request.product_key,
            content_digest=request.content_digest,artifact_digest=header.artifact_digest)]
    elif request.view=='sections':
        item=table('kb.native_document_item')
        rows=[dict(r) for r in conn.execute(select(item).where(item.c.task_id==request.task_id,
            item.c.product_key==request.product_key,item.c.label.in_(['section','chapter']),
            item.c.ordinal>after).order_by(item.c.ordinal).limit(request.limit)).mappings()]
    elif request.view in {'item','formula','cell','regions','trace'}:
        if request.pointer is None or len(rows)!=1:
            raise ValueError('native occurrence inspection requires one existing pointer')
        if request.view in {'regions','trace'}:
            rows=read_native_regions(conn,**pin,pointer=request.pointer)
            if request.view=='trace':
                rows=[dict(row,artifact_digest=header.artifact_digest,space='pdf_points') for row in rows]
        else:
            # Transfer only the selected native object, not its containing document.
            parts=request.pointer.removeprefix('#/').split('/')
            native=conn.execute(select(products.c.native_json[tuple(parts)]).where(
                products.c.task_id==request.task_id,products.c.product_key==request.product_key)).scalar_one()
            if not isinstance(native,dict):
                raise ValueError('native item object unavailable')
            if request.view=='cell':
                cells=native.get('data',{}).get('table_cells',[])
                if request.cell_index is None or request.cell_index>=len(cells):
                    raise ValueError('table cell index unavailable')
                rows=[dict(pointer=request.pointer,cell_index=request.cell_index,cell=cells[request.cell_index])]
            elif request.view=='formula':
                if native.get('label')!='formula':
                    raise ValueError('native pointer is not a formula')
                outcomes=header.health.get('formula_outcomes',[])
                health=next((o for o in outcomes if o['pointer']==request.pointer),{'outcome':'unknown'})
                rows=[dict(pointer=request.pointer,original_text=native.get('orig'),
                    recognized_latex=native.get('text'),recognition=health,
                    regions=read_native_regions(conn,**pin,pointer=request.pointer))]
            else:
                rows=[dict(rows[0],native=native)]
    if request.view in {'items','sections'} and len(rows)==request.limit:
        next_cursor=base64.urlsafe_b64encode(json.dumps(dict(selection=request.selection_digest(),
            after=rows[-1]['ordinal']),sort_keys=True).encode()).decode()
    return NativeSourceResponse(selection=request,release_id=header.release_id,
        health=to_jsonable_python(header.health),rows=to_jsonable_python(rows),next_cursor=next_cursor)


def export_native_source(conn: Connection, request: NativeSourceRequest, destination, *, format: Literal['jsonl','parquet']='parquet') -> None:
    """Stream pinned native projections; publish a detached file only on full completion."""
    import os
    from pathlib import Path
    from collections import defaultdict
    from sqlalchemy import text
    import pyarrow as pa
    import pyarrow.parquet as pq

    destination=Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    if request.view not in {'items','sections'}:
        raise ValueError('streaming native export requires items or sections')
    # Existing typed SQL projection determines Arrow types, retaining the original text.
    from corpus_structure.semantic.metadata import table
    from corpus_structure.schema.interchange import _sql_arrow
    relation=table('kb.native_document_item')
    schema=pa.schema([pa.field(c.name,_sql_arrow(c.type),nullable=bool(c.nullable))
        for c in relation.columns]+[pa.field('content_digest',pa.string(),nullable=False),
            pa.field('native_json',pa.json_(pa.string())),
            pa.field('regions',pa.list_(pa.struct([
                pa.field('region_index',pa.int64()),pa.field('page_no',pa.int64()),
                *[pa.field(n,pa.float64()) for n in ('page_width','page_height','left','top','right','bottom')],
                pa.field('origin',pa.string())])))])
    schema=schema.with_metadata({b'source_selection':request.model_dump_json().encode()})
    temporary=destination.with_name(destination.name+'.partial')
    with temporary.open('xb') as stream:
        writer=pq.ParquetWriter(stream,schema,store_schema=True) if format=='parquet' else None
        try:
            selected=request
            while True:
                response=inspect_native_source(conn,selected)
                pointers=[row['pointer'] for row in response.rows]
                region=table('kb.native_document_region')
                by_pointer=defaultdict(list)
                for r in conn.execute(select(region).where(region.c.task_id==request.task_id,
                    region.c.product_key==request.product_key,region.c.pointer.in_(pointers))).mappings():
                    by_pointer[r['pointer']].append({n:(float(r[n]) if n in {'page_width','page_height','left','top','right','bottom'} else r[n]) for n in ('region_index','page_no','page_width','page_height','left','top','right','bottom','origin')})
                native={r['pointer']:r['native'] for r in conn.execute(text('''SELECT refs.pointer,
                    p.native_json #> string_to_array(substr(refs.pointer,3),'/') AS native
                    FROM ops.native_document_product p CROSS JOIN unnest(CAST(:refs AS text[])) refs(pointer)
                    WHERE p.task_id=:task AND p.product_key=:key AND p.content_digest=:digest'''),
                    dict(refs=pointers,task=request.task_id,key=request.product_key,digest=request.content_digest)).mappings()}
                rows=[dict(row,content_digest=request.content_digest,
                    native_json=json.dumps(native[row['pointer']],ensure_ascii=False,allow_nan=False),
                    regions=sorted(by_pointer[row['pointer']],key=lambda r:r['region_index'])) for row in response.rows]
                if writer is not None:
                    writer.write_batch(pa.RecordBatch.from_pylist(rows,schema=schema))
                else:
                    for row in rows:
                        stream.write((json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n').encode())
                if response.next_cursor is None:
                    break
                selected=selected.model_copy(update={'cursor':response.next_cursor})
        finally:
            if writer is not None:
                writer.close()
    os.link(temporary,destination)
    temporary.unlink()
