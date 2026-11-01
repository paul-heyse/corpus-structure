"""Model-governed frozen PDF preparation, native validation and publication.

SQLAlchemy owns sessions and transactions. A finite DB-free child receives an
owned capture of the actual frozen union; its callback result does not replace
PostgreSQL's independent value, graph and byte enforcement.
"""
from __future__ import annotations

import json
import multiprocessing
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
from sqlalchemy import Connection, Engine, text

from .pdf_staging import PdfBuildRef, _parameters


@dataclass(frozen=True, slots=True)
class FrozenPdfBuildRef:
    build: PdfBuildRef
    frozen_digest: str
    kind: str


@dataclass(frozen=True, slots=True)
class PdfValidationOutcome:
    frozen_digest: str
    logical_digest: str
    contract_digest: str


@dataclass(frozen=True, slots=True)
class PublishedPdfDocumentRef:
    build_id: str
    task_id: int
    product_key: str
    logical_digest: str
    release_id: str
    source_digest: str
    schema_digest: str
    recipe_digest: str
    frozen_digest: str
    kind: str

    @property
    def product_id(self) -> str:
        return self.build_id

    @property
    def revision_id(self) -> str:
        return self.build_id

    @property
    def content_digest(self) -> str:
        """Qualified record identity, never historical canonical-envelope SHA."""
        return self.logical_digest


def _published(row: Mapping[str, Any]) -> PublishedPdfDocumentRef:
    return PublishedPdfDocumentRef(**{key: row[key] for key in PublishedPdfDocumentRef.__dataclass_fields__})


def published_pdf_revision(conn: Connection, task_id: int, product_key: str,
                           logical_digest: str) -> PublishedPdfDocumentRef | None:
    row = conn.execute(text("SELECT * FROM ops.read_pdf_published_revision(:task,:key,:digest)"),
                       dict(task=task_id,key=product_key,digest=logical_digest)).mappings().one_or_none()
    return None if row is None else _published(row)


def freeze_pdf_build(conn: Connection, build: PdfBuildRef, *, kind: str) -> FrozenPdfBuildRef:
    digest = conn.execute(text("SELECT ops.freeze_pdf_build(:build,:task,:attempt,:holder,:kind)"),
                          {**_parameters(build),"kind":kind}).scalar_one()
    return FrozenPdfBuildRef(build, digest, kind)


def prepare_pdf_build(conn: Connection, frozen: FrozenPdfBuildRef) -> None:
    conn.execute(text("SELECT ops.prepare_pdf_build(:build,:task,:attempt,:holder,:frozen)"),
                 {**_parameters(frozen.build),"frozen":frozen.frozen_digest})


def adopt_pdf_companion_batch(conn: Connection, build: PdfBuildRef, family: str,
                              records: Iterable[Mapping[str, Any]], replay_key: str, *, start_ordinal: int = 0) -> None:
    """Adopt bounded complete typed rows; relation endpoints are independent rows."""
    for ordinal, record in enumerate(records, start=start_ordinal):
        body = dict(record)
        local = str(body.get({'occurrence':'occurrence_id','relation':'relation_id',
                             'coverage':'coverage_id'}.get(family,''),ordinal))
        if family=='native_metadata':
            local=f"{body['kind']}:{body['ordinal']}"
        conn.execute(text("SELECT ops.adopt_pdf_companion(:build,:task,:attempt,:holder,:family,:local,CAST(:body AS jsonb),:key,:ordinal)"),
                     {**_parameters(build),'family':family,'local':local,
                      'body':json.dumps(body,ensure_ascii=False,allow_nan=False),
                      'key':f'{replay_key}:{ordinal}','ordinal':ordinal})


_CAPTURE_SCHEMA = pa.schema([pa.field('family',pa.string(),nullable=False),
                             pa.field('body',pa.large_string(),nullable=False)])
_FAMILIES=('header','native','membership','reference','artifact_stream','artifact_part',
           'companion','endpoint')


def _native_validation_child(capture: str, projection: str, result: Any) -> None:
    """One explicitly materialized native oracle, no database handles or credentials."""
    try:
        from .pdf_records import reconstruct_native_document, validate_native_callbacks
        rows: dict[str,list[dict[str,Any]]]={name:[] for name in _FAMILIES}
        with pa.memory_map(capture,'r') as source:
            reader=pa.ipc.open_file(source)
            for index in range(reader.num_record_batches):
                batch=reader.get_batch(index)
                for family,body in zip(batch.column('family').to_pylist(),batch.column('body').to_pylist(),strict=True):
                    rows[family].append(json.loads(body))
        natives={r['record_id']:r for r in rows['native']}
        members: dict[tuple[str,str],list[dict[str,Any]]]={}
        for row in rows['membership']:
            members.setdefault((row['parent_id'],row['field_name']),[]).append(row)
        parts: dict[str,list[dict[str,Any]]]={}
        for row in rows['artifact_part']:
            parts.setdefault(row['stream_id'],[]).append(row)
        for values in members.values():values.sort(key=lambda r:r['ordinal'])
        for values in parts.values():values.sort(key=lambda r:r['ordinal'])
        class Reader:
            def record(self,record_id):
                row=dict(natives[record_id])
                for key in ('scalars_json','structure_json'):row[key]=json.dumps(row[key])
                return row
            def members(self,parent_id,field_name):
                for member in members.get((parent_id,field_name),()):
                    row=dict(member)
                    if row.get('scalar_json') is not None:row['scalar_json']=json.dumps(row['scalar_json'])
                    yield {k:v for k,v in row.items() if v is not None}
            def scalar(self,stream_id):
                for part in parts.get(stream_id,()):
                    yield bytes.fromhex(part['body'].removeprefix('\\x'))
        profiles={r['stream_id']:r['encoding_profile'] for r in rows['artifact_stream']}
        document=reconstruct_native_document(Reader(),rows['header'][0]['root_id'],scalar_profiles=profiles)
        validate_native_callbacks(document)
        # Source access is a derived, per-item projection, never the content authority.
        nodes={}
        for key in ('body','furniture'):
            node=document.get(key)
            if node:nodes[node['self_ref']]=node
        for key in ('groups','texts','pictures','tables','key_value_items','form_items'):
            for node in document.get(key,[]):nodes[node['self_ref']]=node
        order=[];seen=set()
        def walk(pointer):
            if pointer in seen:raise ValueError('native containment repeats an item')
            seen.add(pointer);order.append(pointer)
            for child in nodes[pointer].get('children',[]):walk(child['$ref'])
        walk(document['body']['self_ref']);walk(document['furniture']['self_ref'])
        order.extend(sorted(set(nodes)-seen))
        sections={p for p,n in nodes.items() if n.get('label') in ('section','chapter')}
        # Organized section groups use section/chapter labels; keep the native labels.
        with Path(projection).open('w') as out:
            for ordinal,pointer in enumerate(order):
                node=nodes[pointer];parent=node.get('parent',{}).get('$ref');owner=pointer
                visited=set()
                while owner not in sections and nodes[owner].get('parent'):
                    if owner in visited:raise ValueError('cyclic source section ancestry')
                    visited.add(owner);owner=nodes[owner]['parent']['$ref']
                row=dict(pointer=pointer,ordinal=ordinal,label=node.get('label','unspecified'),
                         parent_pointer=parent,section_pointer=owner if owner in sections else None,
                         content_layer=node.get('content_layer','body'),text=node.get('text'),native_json=node)
                out.write(json.dumps({'family':'access','body':row},ensure_ascii=False,allow_nan=False)+'\n')
                for index,prov in enumerate(node.get('prov',[])):
                    page=document['pages'][str(prov['page_no'])];box=prov['bbox']
                    region=dict(pointer=pointer,region_index=index,page_no=prov['page_no'],
                                page_width=page['size']['width'],page_height=page['size']['height'],
                                left=box['l'],top=box['t'],right=box['r'],bottom=box['b'],
                                origin='top_left' if box['coord_origin']=='TOPLEFT' else 'bottom_left')
                    out.write(json.dumps({'family':'region','body':region})+'\n')
        result.send((True,None))
    except BaseException as error:
        result.send((False,f'{type(error).__name__}: {error}'))
    finally:result.close()


def validate_pdf_build(engine: Engine, frozen: FrozenPdfBuildRef,
                       check_active: Callable[[],None] | None=None) -> PdfValidationOutcome:
    check_active=check_active or (lambda:None)
    params={**_parameters(frozen.build),'frozen':frozen.frozen_digest}
    check_active()
    with engine.begin() as conn:
        from .contracts import require_database_operation
        require_database_operation(conn,frozen.build.release_id,'validate_pdf_build')
        existing=conn.execute(text("SELECT * FROM ops.lookup_pdf_validation(:build,:task,:attempt,:holder,:frozen)"),params).mappings().one_or_none()
    if existing is not None:
        return PdfValidationOutcome(existing['frozen_digest'],existing['logical_digest'],existing['contract_digest'])
    with tempfile.TemporaryDirectory(prefix='pdf-native-validation-') as directory:
        capture=Path(directory)/'frozen.arrow';projection=Path(directory)/'access.jsonl'
        with pa.OSFile(str(capture),'wb') as sink, pa.ipc.new_file(sink,_CAPTURE_SCHEMA) as writer:
            for family in ('header','native','membership','artifact_stream','artifact_part'):
                after=None
                while True:
                    check_active()
                    with engine.begin() as conn:
                        values=conn.execute(text("SELECT * FROM ops.read_pdf_frozen_rows(:build,:task,:attempt,:holder,:frozen,:family,CAST(:after AS jsonb),256)"),
                            {**params,'family':family,'after':json.dumps(after) if after is not None else None}).scalars().all()
                    if not values:break
                    after=values[-1]['_cursor']
                    for row in values:row.pop('_cursor',None)
                    writer.write_batch(pa.RecordBatch.from_arrays([pa.array([family]*len(values)),
                        pa.array([json.dumps(r) for r in values],type=pa.large_string())],schema=_CAPTURE_SCHEMA))
        context=multiprocessing.get_context('spawn');parent,child=context.Pipe(duplex=False)
        process=context.Process(target=_native_validation_child,args=(str(capture),str(projection),child))
        process.start();child.close()
        try:
            while not parent.poll(0.2):
                check_active()
                if not process.is_alive():raise RuntimeError('native validation child exited without outcome')
            passed,error=parent.recv()
            if not passed:raise ValueError(error)
            with engine.begin() as conn:
                conn.execute(text("SELECT ops.record_pdf_native_validation(:build,:task,:attempt,:holder,:frozen,true)"),params)
            process.join(5)
            if process.is_alive():raise RuntimeError('native validation child did not settle')
        finally:
            if process.is_alive():process.terminate();process.join(5)
            if process.is_alive():process.kill();process.join()
            parent.close();process.close()
        with projection.open() as source:
            pending = []
            size = 0
            def adopt_projection(rows):
                with engine.begin() as conn:
                    conn.execute(text("SELECT ops.adopt_pdf_access_batch(:build,:task,:attempt,:holder,:frozen,CAST(:rows AS jsonb))"),
                                 {**params,'rows':json.dumps(rows)})
            for line in source:
                check_active()
                if pending and (size + len(line.encode()) > 8*1024**2 or len(pending) >= 128):
                    adopt_projection(pending);pending=[];size=0
                pending.append(json.loads(line));size += len(line.encode())
            if pending:adopt_projection(pending)
        check_active()
        with engine.begin() as conn:
            row=conn.execute(text("SELECT * FROM ops.validate_pdf_build(:build,:task,:attempt,:holder,:frozen)"),params).mappings().one()
        return PdfValidationOutcome(row['frozen_digest'],row['logical_digest'],row['contract_digest'])


def seal_pdf_build(conn: Connection,frozen: FrozenPdfBuildRef,
                   product_key: str='integrated') -> PublishedPdfDocumentRef:
    row=conn.execute(text("SELECT * FROM ops.seal_pdf_build(:build,:task,:attempt,:holder,:frozen,:key)"),
                     {**_parameters(frozen.build),'frozen':frozen.frozen_digest,'key':product_key}).mappings().one()
    return _published(row)


def retain_pdf_stage_recipe(conn: Connection, *, task_id: int, attempt: int,
                            holder: str, recipe_bytes: bytes) -> str:
    return conn.execute(text("SELECT ops.bind_pdf_stage_recipe(:task,:attempt,:holder,:recipe)"),
                        dict(task=task_id,attempt=attempt,holder=holder,recipe=recipe_bytes)).scalar_one()


@dataclass(frozen=True, slots=True)
class PdfBuildState:
    build: PdfBuildRef
    state: str
    frozen: FrozenPdfBuildRef | None
    published: PublishedPdfDocumentRef | None


def inspect_pdf_build(conn: Connection, *, task_id: int, attempt: int, holder: str,
                      replay_key: str) -> PdfBuildState | None:
    row=conn.execute(text("SELECT * FROM ops.lookup_pdf_build(:task,:attempt,:holder,:key)"),
                     dict(task=task_id,attempt=attempt,holder=holder,key=replay_key)).mappings().one_or_none()
    if row is None:return None
    build=PdfBuildRef(**{key:row[key] for key in PdfBuildRef.__dataclass_fields__})
    params=dict(build=build.build_id,task=task_id,attempt=attempt,holder=holder)
    digest=conn.execute(text("SELECT ops.lookup_pdf_frozen_digest(:build,:task,:attempt,:holder)"),params).scalar_one()
    kind=conn.execute(text("SELECT ops.lookup_pdf_frozen_kind(:build,:task,:attempt,:holder)"),params).scalar_one()
    published=None
    if row['state']=='published':
        value=conn.execute(text("SELECT * FROM ops.lookup_pdf_published_build(:build,:task,:attempt,:holder)"),params).mappings().one()
        published=_published(value)
    return PdfBuildState(build,row['state'],FrozenPdfBuildRef(build,digest,kind) if digest else None,published)
