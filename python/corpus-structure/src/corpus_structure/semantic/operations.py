"""Run-bound source operations over the trusted semantic physical model.

Database sequence IDs locate rows only. Reproducible source observations bind the immutable
release, method input and source item; task attempts and sequence IDs do not enter their keys.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping, Sequence
from sqlalchemy import Connection, select, insert, update, text, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .identity import canonical_bytes
from .metadata import table
from .types import PreparedRelease

class OperationConflict(ValueError):
    """Immutable input identity changed or a task/pass fence was lost."""

@dataclass(frozen=True)
class OperationBinding:
    release_id: str
    input_realization_id: str
    input_revision: int
    dependencies: bytes

    def __post_init__(self) -> None:
        import json
        if not self.release_id or not self.input_realization_id or self.input_revision < 0:
            raise ValueError("operation requires release, realization and nonnegative revision")
        if canonical_bytes(json.loads(self.dependencies)) != self.dependencies:
            raise ValueError("dependencies must be canonical immutable JSON bytes")

    @property
    def dependency_digest(self) -> str:
        return sha256(self.dependencies).hexdigest()


def create_run(conn: Connection, *, project_id: str, binding: OperationBinding,
               kind: str, options: Mapping[str,Any], code_commit: str,
               guideline: str = "", phase: int = 0) -> int:
    import json
    try:
        return conn.execute(text("SELECT ops.create_run(:p,:r,:z,:v,:d,:k,:phase,CAST(:opts AS jsonb),:g,:commit)"),
            dict(p=project_id,r=binding.release_id,z=binding.input_realization_id,v=binding.input_revision,
                 d=binding.dependencies,k=kind,phase=phase,opts=json.dumps(options),g=guideline,commit=code_commit)).scalar_one()
    except Exception as exc:
        if getattr(getattr(exc, 'orig', None), 'sqlstate', None)=='P0004':
            raise OperationConflict('input realization changed before run creation') from exc
        raise



def binding_of(conn:Connection,run_id:int)->OperationBinding:
    r=table('ops.run'); row=conn.execute(select(r).where(r.c.id==run_id)).mappings().one()
    return OperationBinding(row['release_id'],row['input_realization_id'],row['input_revision'],bytes(row['dependencies']))


def record_method(conn:Connection, method:Any, name:str, params:Mapping[str,Any],config_hash:str)->int:
    m=table('ops.method'); c=table('ops.method_config')
    values=dict(name=method.name,version=method.version,family=str(method.family),tier=str(method.tier),confidence_source=str(method.confidence_source) if method.confidence_source is not None else None)
    conn.execute(pg_insert(m).values(**values).on_conflict_do_nothing())
    mid=conn.execute(select(m.c.id).where(m.c.name==method.name,m.c.version==method.version)).scalar_one()
    conn.execute(pg_insert(c).values(method_id=mid,name=name,params=dict(params),config_hash=config_hash).on_conflict_do_nothing())
    row=conn.execute(select(c).where(c.c.method_id==mid,c.c.config_hash==config_hash)).mappings().one()
    if row['params'] != dict(params):raise OperationConflict('configuration hash denotes different parameters')
    return row['id']


def create_task(conn:Connection, *,run_id:int,config_id:int,stage:str,unit_type:str,
                input_hash:str,unit_id:int|None=None,unit_key:str|None=None,
                packet_hash:str|None=None,agent:bool=False)->int:
    r=table('ops.run'); run=conn.execute(select(r).where(r.c.id==run_id).with_for_update(read=True)).mappings().one()
    if run['sealed'] or run['status'] not in {'created','running'}:raise OperationConflict('run no longer accepts tasks')
    t=table('ops.task')
    return conn.execute(insert(t).values(run_id=run_id,release_id=run['release_id'],
        stage=stage,unit_type=unit_type,unit_id=unit_id,unit_key=unit_key,method_config_id=config_id,
        input_hash=input_hash,packet_hash=packet_hash,status='awaiting_agent' if agent else 'pending',
        attempt=0,cost={},priority=0,created_at=func.clock_timestamp()).returning(t.c.id)).scalar_one()


def claim_tasks(conn:Connection, *,run_id:int, config_id:int,holder:str,limit:int=1,
                agent:bool=False)->list[dict[str,Any]]:
    if limit<1:raise ValueError('positive claim limit required')
    t=table('ops.task');r=table('ops.run')
    run=conn.execute(select(r).where(r.c.id==run_id).with_for_update(read=True)).mappings().one()
    if run['sealed'] or run['status'] not in {'created','running'}:return []
    eligible=(t.c.status=='awaiting_agent') if agent else (t.c.status=='pending')
    eligible=eligible | ((t.c.status=='running') & (t.c.lease_until<func.clock_timestamp()))
    ids=select(t.c.id).where(t.c.run_id==run_id,t.c.method_config_id==config_id,eligible).order_by(t.c.priority.desc(),t.c.id).limit(limit).with_for_update(skip_locked=True).cte('c').prefix_with('MATERIALIZED')
    rows=conn.execute(update(t).where(t.c.id==ids.c.id).values(status='running',attempt=t.c.attempt+1,claimed_by=holder,lease_until=func.clock_timestamp()+text("interval '5 minutes'"),started_at=func.coalesce(t.c.started_at,func.clock_timestamp())).returning(t)).mappings()
    return [dict(row) for row in rows]


def observation_key(binding:OperationBinding,input_hash:str,definition:str,item_key:str)->str:
    return 'observation:'+sha256(canonical_bytes([binding.release_id,binding.dependency_digest,input_hash,definition,item_key])).hexdigest()


def complete_task(conn:Connection, *,task_id:int,attempt:int,holder:str,
                  prepared:PreparedRelease,observations:Sequence[Mapping[str,Any]],
                  outcome:str='done',error:Mapping[str,Any]|None=None)->list[int]:
    """Validate the bound producer envelope, then atomically fence and append source results."""
    if outcome not in {'done','empty','failed'}:raise ValueError('invalid terminal outcome')
    if (outcome=='done') != bool(observations):raise ValueError('terminal outcome contradicts observations')
    if (outcome=='failed') != bool(error):raise ValueError('failure requires explicit error')
    t=table('ops.task'); task=conn.execute(select(t).where(t.c.id==task_id)).mappings().one()
    binding=binding_of(conn,task['run_id'])
    if prepared.release_id!=binding.release_id:raise OperationConflict('wrong producer release')
    rows=[]
    for ordinal,raw in enumerate(observations):
        data=dict(raw); definition=data.pop('payload_definition'); item=data.pop('item_key')
        payload=prepared.validate_python(definition,data.pop('payload')).model_dump(mode='json')
        rows.append(dict(data,ordinal=ordinal,payload_definition=definition,payload=payload,
            observation_key=observation_key(binding,task['input_hash'],definition,item)))
    import json
    result=conn.execute(text('SELECT ops.complete_task(:task,:attempt,:holder,CAST(:rows AS jsonb),:outcome,CAST(:error AS jsonb))'),dict(task=task_id,attempt=attempt,holder=holder,rows=json.dumps(rows),outcome=outcome,error=json.dumps(error))).scalar_one()
    return list(result)


def seal_cut(conn:Connection,run_id:int,name:str,*,final:bool=False)->int:
    return conn.execute(text('SELECT ops.capture_cut(:run,:name,:final)'),dict(run=run_id,name=name,final=final)).scalar_one()


def cut_observations(conn:Connection,cut_id:int)->list[dict[str,Any]]:
    o=table('kb.observation');c=table('ops.cut_task')
    return [dict(row) for row in conn.execute(select(o).join(c,o.c.task_id==c.c.origin_task_id).where(c.c.cut_id==cut_id).order_by(o.c.observation_key)).mappings()]


def register_document(conn:Connection, *, project_id:str, source_uri:str, original_path:str,
                      original:bytes, mime:str='text/html', title:str|None=None,
                      metadata:Mapping[str,Any]|None=None)->int:
    from pathlib import Path
    if Path(original_path).read_bytes()!=original:
        raise OperationConflict('retained original bytes differ from registered source')
    content_hash=sha256(original).hexdigest()
    key='source:'+sha256(canonical_bytes([project_id,source_uri,content_hash])).hexdigest()
    t=table('kb.document'); values=dict(project_id=project_id,source_key=key,source_uri=source_uri,
        content_hash=content_hash,original_path=original_path,mime=mime,title=title,metadata=dict(metadata or {}))
    conn.execute(pg_insert(t).values(**values).on_conflict_do_nothing())
    row=conn.execute(select(t).where(t.c.project_id==project_id,t.c.source_key==key)).mappings().one()
    if any(row[k]!=v for k,v in values.items()):raise OperationConflict('source identity denotes another source descriptor')
    return row['id']


def read_original(conn:Connection,document_id:int)->bytes:
    from pathlib import Path
    t=table('kb.document');row=conn.execute(select(t).where(t.c.id==document_id)).mappings().one()
    data=Path(row['original_path']).read_bytes()
    if sha256(data).hexdigest()!=row['content_hash']:raise OperationConflict('retained original content changed')
    return data


def store_rendition(conn:Connection, *,run_id:int,document_id:int,content:Any,
                    task_id:int,config_id:int,parse_detail:Mapping[str,Any])->int:
    """Preserve physical content sharing separately from method build provenance."""
    payload=content.model_dump(mode='json')
    digest=sha256(canonical_bytes(payload)).hexdigest()
    d=table('kb.document');source=conn.execute(select(d.c.source_key).where(d.c.id==document_id)).scalar_one()
    key='rendition:'+sha256(canonical_bytes([source,digest])).hexdigest()
    t=table('kb.rendition');values=dict(document_id=document_id,rendition_key=key,content_digest=digest,
        canonical_text=content.canonical_text,content=payload,parse_status=str(content.parse_status))
    conn.execute(pg_insert(t).values(**values).on_conflict_do_nothing())
    row=conn.execute(select(t).where(t.c.rendition_key==key)).mappings().one()
    if any(row[k]!=v for k,v in values.items()):raise OperationConflict('rendition identity denotes different content')
    rendition_id=row['id']; st=table('kb.segment')
    def put(segment:Any,parent:str|None=None)->None:
        skey='segment:'+sha256(canonical_bytes([key,str(segment.kind),segment.start,segment.end])).hexdigest()
        conn.execute(pg_insert(st).values(rendition_id=rendition_id,segment_key=skey,parent_key=parent,
            kind=str(segment.kind),ordinal=segment.ordinal,start_offset=segment.start,end_offset=segment.end,
            attrs=dict(segment.attrs),parse_status=str(segment.parse_status),parse_reason=segment.parse_reason).on_conflict_do_nothing())
        for child in segment.children:put(child,skey)
    put(content.document)
    b=table('ops.rendition_build');build=dict(document_id=document_id,method_config_id=config_id,
        rendition_id=rendition_id,task_id=task_id,parse_detail=dict(parse_detail))
    conn.execute(pg_insert(b).values(**build).on_conflict_do_nothing())
    prev=conn.execute(select(b).where(b.c.document_id==document_id,b.c.method_config_id==config_id)).mappings().one()
    if prev['rendition_id']!=rendition_id:raise OperationConflict('deterministic rendition build changed content')
    rr=table('ops.run_rendition')
    conn.execute(pg_insert(rr).values(run_id=run_id,document_id=document_id,rendition_id=rendition_id).on_conflict_do_nothing())
    chosen=conn.execute(select(rr.c.rendition_id).where(rr.c.run_id==run_id,rr.c.document_id==document_id)).scalar_one()
    if chosen!=rendition_id:raise OperationConflict('run already selected another source rendition')
    return rendition_id


def read_rendition(conn:Connection,rendition_id:int)->Any:
    from corpus_structure.core.evidence import RenditionContent
    t=table('kb.rendition');payload=conn.execute(select(t.c.content).where(t.c.id==rendition_id)).scalar_one()
    return RenditionContent.model_validate(payload)
