"""Fact explanations and unit source-custody snapshots from the completed final cut."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel,ConfigDict,JsonValue
from sqlalchemy import and_,select
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import Explanation as FactExplanation,SnapshotBinding
from corpus_structure.serve.journey import bind_session,QueryRefused
class UnitTask(BaseModel):
    task_id:int
    origin_task_id:int|None
    method:str
    operation_version:str
    input_hash:str
    included_in_cut:bool
    source_result:dict[str,JsonValue]|None
class UnitExplanation(BaseModel):
    cut_id:int
    unit_key:str
    tasks:tuple[UnitTask,...]
    observations:tuple[dict[str,JsonValue],...]
class Explanation(BaseModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    run_id:int
    binding:SnapshotBinding
    kind:Literal["claim","unit"]
    identifier:str
    detail:FactExplanation|UnitExplanation

def explain(conn,run_id,kind:Literal["claim","unit"],key):
    session=bind_session(conn,run_id)
    if kind == "claim":
        try: detail=session.explain(key)
        except KeyError: raise QueryRefused(f"no semantic fact {key}") from None
    else:
        completed,t,ct,result,config,method,observation=(table(n) for n in ("ops.completed_result","ops.task","ops.cut_task","ops.task_result","ops.method_config","ops.method","kb.observation"))
        cut=conn.execute(select(completed.c.cut_id).where(completed.c.run_id == run_id)).scalar_one()
        rows=conn.execute(select(t.c.id,t.c.input_hash,ct.c.origin_task_id,method.c.name,method.c.version,result.c.body).select_from(t.join(config,t.c.method_config_id == config.c.id).join(method,config.c.method_id == method.c.id).outerjoin(ct,and_(ct.c.task_id == t.c.id,ct.c.cut_id == cut)).outerjoin(result,result.c.task_id == ct.c.origin_task_id)).where(t.c.run_id == run_id,t.c.unit_key == key).order_by(t.c.id)).mappings().all()
        if not rows: raise QueryRefused(f"no source unit {key}")
        origins={row["origin_task_id"] for row in rows if row["origin_task_id"] is not None}
        observations=tuple({"observation_id":r["id"],"observation_key":r["observation_key"],"task_id":r["task_id"],"kind":r["kind"],"payload":r["payload"]} for r in conn.execute(select(observation).where(observation.c.task_id.in_(origins)).order_by(observation.c.observation_key)).mappings())
        detail=UnitExplanation(cut_id=cut,unit_key=key,tasks=tuple(UnitTask(task_id=row["id"],origin_task_id=row["origin_task_id"],method=row["name"],operation_version=row["version"],input_hash=row["input_hash"],included_in_cut=row["origin_task_id"] is not None,source_result=row["body"]) for row in rows),observations=observations)
    return Explanation(run_id=run_id,binding=session.binding,kind=kind,identifier=key,detail=detail)
