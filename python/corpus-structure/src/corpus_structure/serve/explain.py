"""Explanations pinned to the run's cut and sealed final M19 task (D8)."""
from __future__ import annotations
from typing import Any,Literal
from pydantic import BaseModel,ConfigDict,JsonValue
from sqlalchemy import select,or_,text,func
from corpus_structure.core._model.shapes import VerificationPayload
from corpus_structure.serve.results import ClaimAnswer
from corpus_structure.serve.protocol import QueryContext
from corpus_structure.serve.journey import check_finished,QueryRefused
from corpus_structure.core.db import metadata

T=metadata.tables
class Support(BaseModel):
    observation:int
    task:int
    method:str
    configuration:str|None=None
class Link(BaseModel):
    from_key:str
    to_key:str
    kind:str
    detail:JsonValue
class ClaimExplanation(BaseModel):
    claim:ClaimAnswer
    supports:list[Support]
    supports_remaining:int
    links:list[Link]
    links_remaining:int
    alternatives:list[ClaimAnswer]
    verification:list[VerificationPayload]
    m19_task_id:int|None
    judgments:list[JsonValue]
class TaskExplanation(BaseModel):
    id:int
    stage:str
    method:str
    rule_key:str|None
    trigger_metrics:JsonValue
    status:str
    reason:str|None
    cost:JsonValue
class FateExplanation(BaseModel):
    fate:str
    reason:str|None
class UnitExplanation(BaseModel):
    tasks:list[TaskExplanation]
    fates:list[FateExplanation]
class Explanation(BaseModel):
    model_config=ConfigDict(frozen=True)
    run_id:int
    kind:Literal['claim','unit']
    key:str
    detail:ClaimExplanation|UnitExplanation

def explain(conn:Any,run_id:int,kind:Literal['claim','unit'],key:str)->Explanation:
    check_finished(conn,run_id)
    ctx=QueryContext(run_id,conn)
    if kind=='unit':
        from corpus_structure.orchestrate.fates import fates
        fate=fates(conn,run_id,unit_keys=[key])
        rows=conn.execute(text("SELECT t.id,t.stage,m.name AS method,pr.rule_key,t.trigger_metrics,t.status,t.reason,t.cost,t.finished_at,r.cut_at FROM ops.task t JOIN ops.run r ON r.id=t.run_id JOIN ops.method_config mc ON mc.id=t.method_config_id JOIN ops.method m ON m.id=mc.method_id LEFT JOIN ops.policy_rule pr ON pr.id=t.trigger_rule_id WHERE t.run_id=:r AND t.unit_key=:k ORDER BY t.id"),{'r':run_id,'k':key}).mappings()
        tasks=[]
        for r in rows:
            tasks.append({k:v for k,v in dict(r).items() if k not in ('finished_at','cut_at') }|{'status':r['status'] if r['finished_at'] and r['finished_at']<=r['cut_at'] else 'unresolved'})
        detail=UnitExplanation(tasks=tasks,fates=[{'fate':f.fate,'reason':f.reason.value if f.reason else None} for f in fate])
    else:
        claim=next(ctx.reader.claims(key=key,include_candidates=True,include_suppositions=True,with_premises=False),None)
        if claim is None: raise QueryRefused(f'no claim {key}')
        c,cs,o,t,mc,m,link,r=T['kb.claim'],T['kb.claim_support'],T['kb.observation'],T['ops.task'],T['ops.method_config'],T['ops.method'],T['kb.claim_link'],T['ops.run']
        id_=conn.execute(select(c.c.id).where(c.c.run_id==run_id,c.c.key==key)).scalar_one()
        supports_count=conn.execute(select(func.count()).select_from(cs).where(cs.c.claim_id==id_)).scalar_one()
        supports=[dict(x) for x in conn.execute(select(o.c.id.label('observation'),t.c.id.label('task'),m.c.name.label('method'),mc.c.name.label('configuration')).select_from(cs).join(o,o.c.id==cs.c.observation_id).join(t,t.c.id==o.c.task_id).join(mc,mc.c.id==t.c.method_config_id).join(m,m.c.id==mc.c.method_id).where(cs.c.claim_id==id_).order_by(o.c.id).limit(10)).mappings()]
        link_filter=(link.c.run_id==run_id)&or_(link.c.from_claim_id==id_,link.c.to_claim_id==id_)
        links_count=conn.execute(select(func.count()).select_from(link).where(link_filter)).scalar_one()
        source,target=c.alias('source'),c.alias('target')
        links=[dict(x) for x in conn.execute(select(source.c.key.label('from_key'),target.c.key.label('to_key'),link.c.link_type.label('kind'),link.c.detail).select_from(link).join(source,source.c.id==link.c.from_claim_id).join(target,target.c.id==link.c.to_claim_id).where(link_filter).order_by(source.c.key,link.c.link_type,target.c.key).limit(10)).mappings()]
        alternatives=select(c.c.key).where(c.c.id.in_(select(link.c.to_claim_id).where(link.c.run_id==run_id,link.c.from_claim_id==id_,link.c.link_type=='alternative_of'))|c.c.id.in_(select(link.c.from_claim_id).where(link.c.run_id==run_id,link.c.to_claim_id==id_,link.c.link_type=='alternative_of')))
        alternative_rows=list(ctx.reader.claims(statement=select(c).where(c.c.key.in_(alternatives),c.c.run_id==run_id),with_premises=False))
        sealed=conn.execute(select(r.c.cut_m19_task_id).where(r.c.id==run_id)).scalar_one()
        payloads=conn.execute(select(o.c.payload).where(o.c.task_id==sealed,o.c.kind=='verification',o.c.payload['claim_key'].as_string()==key).order_by(o.c.id)).scalars()
        warnings=[VerificationPayload.model_validate(w) for w in payloads]
        detail=ClaimExplanation(claim=claim,supports=supports,supports_remaining=max(0,supports_count-10),links=links,links_remaining=max(0,links_count-10),alternatives=alternative_rows,verification=warnings,m19_task_id=sealed,judgments=[])
    return Explanation(run_id=run_id,kind=kind,key=key,detail=detail)
