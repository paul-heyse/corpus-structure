"""Explanations pinned to the run's cut and sealed final M19 task (D8)."""
from __future__ import annotations
from typing import Any,Literal
from pydantic import BaseModel,ConfigDict,JsonValue
from sqlalchemy import select,or_,text
from corpus_structure.serve.protocol import QueryContext
from corpus_structure.serve.journey import check_finished,QueryRefused
from corpus_structure.core.db import metadata

T=metadata.tables
class Explanation(BaseModel):
    model_config=ConfigDict(frozen=True)
    run_id:int
    kind:Literal['claim','unit']
    key:str
    detail:dict[str,JsonValue]

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
        detail={'tasks':tasks,'fates':[{'fate':f.fate,'reason':str(f.reason) if f.reason else None} for f in fate]}
    else:
        claims=list(ctx.reader.claims(key=key,include_candidates=True,include_suppositions=True))
        if not claims: raise QueryRefused(f'no claim {key}')
        c,cs,o,t,mc,m,link,r=T['kb.claim'],T['kb.claim_support'],T['kb.observation'],T['ops.task'],T['ops.method_config'],T['ops.method'],T['kb.claim_link'],T['ops.run']
        id_=conn.execute(select(c.c.id).where(c.c.run_id==run_id,c.c.key==key)).scalar_one()
        supports=[dict(x) for x in conn.execute(select(o.c.id.label('observation'),t.c.id.label('task'),m.c.name.label('method'),mc.c.name.label('configuration')).select_from(cs).join(o,o.c.id==cs.c.observation_id).join(t,t.c.id==o.c.task_id).join(mc,mc.c.id==t.c.method_config_id).join(m,m.c.id==mc.c.method_id).where(cs.c.claim_id==id_).order_by(o.c.id)).mappings()]
        links=[dict(x) for x in conn.execute(select(link).where(link.c.run_id==run_id,or_(link.c.from_claim_id==id_,link.c.to_claim_id==id_)).order_by(link.c.id)).mappings()]
        sealed=conn.execute(select(r.c.cut_m19_task_id).where(r.c.id==run_id)).scalar_one()
        warnings=list(conn.execute(select(o.c.payload).where(o.c.task_id==sealed,o.c.kind=='verification').order_by(o.c.id)).scalars())
        warnings=[w for w in warnings if w.get('claim_key',w.get('claim')) in (key,None)]
        detail={'claim':claims[0],'supports':supports[:10],'supports_remaining':max(0,len(supports)-10),'links':links[:10],'links_remaining':max(0,len(links)-10),'verification':warnings,'m19_task_id':sealed,'judgments':[]}
    return Explanation(run_id=run_id,kind=kind,key=key,detail=detail)
