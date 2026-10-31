"""Immutable section projections and run selections over pinned native PDF products."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from sqlalchemy import Connection, select, text

from corpus_structure.core.method import SourceViewDraft, SourceViewRef
from .identity import canonical_bytes
from .metadata import table
from .parsing_products import ProductReference


@dataclass(frozen=True)
class PreparedSourceView:
    ref: SourceViewRef
    text: str
    pieces: tuple[dict[str, Any], ...]
    items: tuple[dict[str, Any], ...]
    ancestors: tuple[dict[str, Any], ...]
    health: dict[str, Any]
    text_policy: Any = None

    @cached_property
    def layout(self):
        from corpus_structure.ingest.sentences import Block, SentenceConfig, pipeline, prepare_layout
        native = {item['self_ref']: item for item in self.items}
        math = tuple((p['start'],p['end']) for p in self.pieces
                     if p.get('item_ref') in native and native[p['item_ref']].get('label') == 'formula')
        from .analysis_contracts import prepare_text_policy
        policy=self.text_policy or prepare_text_policy()
        return prepare_layout(pipeline(SentenceConfig()), Block(self.text, math, (), ()),recipe=policy.recipe)

    def context(self) -> dict[str, Any]:
        return dict(pieces=self.pieces,items=self.items,ancestors=self.ancestors,health=self.health)


def _ref(row) -> SourceViewRef:
    return SourceViewRef(row['id'],row['key'],row['document_id'],
        ProductReference(row['native_task_id'],row['native_product_key'],row['native_content_digest']),
        row['section_pointer'],row['membership'],row['projection_digest'],row['recipe_digest'])


def selected_source_views(conn: Connection, run_id: int) -> tuple[SourceViewRef, ...]:
    view, selection = table('kb.source_view'),table('ops.run_source_view')
    newer=selection.alias('newer')
    rows=conn.execute(select(view).join(selection,selection.c.source_view_id==view.c.id)
        .where(selection.c.run_id==run_id, ~select(newer.c.source_view_id).where(newer.c.run_id==run_id,newer.c.supersedes_source_view_id==view.c.id).exists()).order_by(selection.c.position,view.c.id)).mappings()
    return tuple(_ref(row) for row in rows)


def load_source_view(conn: Connection, source_view_id: int) -> PreparedSourceView:
    views=table('kb.source_view')
    row=conn.execute(select(views).where(views.c.id==source_view_id)).mappings().one()
    reference=_ref(row)
    projection=row['projection']
    product=table('ops.native_document_product')
    pointers=tuple(dict.fromkeys([*projection['items'],*projection['ancestors']]))
    # One set-shaped query transfers only selected native values, never the book JSON.
    values=conn.execute(text('''SELECT refs.pointer, p.native_json #> string_to_array(substr(refs.pointer,3),'/') AS item
        FROM ops.native_document_product p CROSS JOIN unnest(CAST(:pointers AS text[])) WITH ORDINALITY refs(pointer,position)
        WHERE p.task_id=:task AND p.product_key=:key AND p.content_digest=:digest ORDER BY refs.position'''),
        dict(pointers=list(pointers),task=reference.native_product.task_id,
             key=reference.native_product.product_key,digest=reference.native_product.content_digest)).mappings()
    native={r['pointer']:r['item'] for r in values}
    if any(native.get(p) is None for p in pointers):
        raise ValueError('source view has lost its pinned native occurrences')
    from .analysis_contracts import prepare_text_policy
    from .releases import open_release
    policy=prepare_text_policy(open_release(conn,row['release_id']))
    return PreparedSourceView(reference,projection['text'],tuple(projection['pieces']),
        tuple(native[p] for p in projection['items']),tuple(native[p] for p in projection['ancestors']),projection['health'],policy)


def store_source_view(conn: Connection, *, run_id: int, task_id: int, attempt: int, holder: str,
                      draft: SourceViewDraft, position: int) -> int:
    from .contracts import require_database_operation
    run=table('ops.run')
    release=conn.execute(select(run.c.release_id).where(run.c.id==run_id)).scalar_one()
    require_database_operation(conn,release,'publish_source_view')
    payload=dict(key=draft.key,document_id=draft.document_id,
        native_task_id=draft.native_product.task_id,native_product_key=draft.native_product.product_key,
        native_content_digest=draft.native_product.content_digest,section_pointer=draft.section_pointer,
        membership=draft.membership,projection_digest=draft.projection_digest,recipe_digest=draft.recipe_digest,
        projection=draft.projection())
    if draft.replaces_source_view_id is not None:
        payload["replaces_source_view_id"]=draft.replaces_source_view_id
    from .pdf_contracts import pdf_context_for_task
    context=pdf_context_for_task(conn,task_id)
    payload=context.boundary.validate_json("PdfSourceViewPublication",json.dumps(payload)).model_dump(mode="json",exclude_none=True)
    return conn.execute(text('SELECT ops.publish_source_view(:run,:task,:attempt,:holder,:position,:payload,:recipe)'),
        dict(run=run_id,task=task_id,attempt=attempt,holder=holder,position=position,
             payload=canonical_bytes(payload),recipe=draft.recipe_bytes)).scalar_one()


def select_reused_source_views(conn: Connection, *, run_id: int, task_id: int) -> None:
    conn.execute(text('SELECT ops.select_reused_source_views(:run,:task)'),dict(run=run_id,task=task_id))


def store_native_source_frame(conn: Connection, *, task_id: int, packet_hash: str,
                              frame: dict[str,Any]) -> None:
    conn.execute(text('SELECT ops.capture_native_source_frame(:task,:hash,CAST(:frame AS jsonb))'),
                 dict(task=task_id,hash=packet_hash,frame=json.dumps(frame)))


def read_native_source(conn,request):
    from corpus_structure.serve.native_source import inspect_native_source
    return inspect_native_source(conn,request)


def request_source_view(*args,**kwargs):
    from .native_requests import request_source_view as request
    return request(*args,**kwargs)


def store_region_artifact(conn,*,task_id,attempt,holder,selection,recipe_bytes,content):
    return conn.execute(text('SELECT ops.publish_pdf_region_artifact(:task,:attempt,:holder,CAST(:selection AS jsonb),:recipe,:content)'),
        dict(task=task_id,attempt=attempt,holder=holder,selection=json.dumps(selection),recipe=recipe_bytes,content=content)).scalar_one()
