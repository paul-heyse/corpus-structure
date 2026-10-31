"""Existing run/task lifecycle applied to explicit native section demands."""
from __future__ import annotations

from dataclasses import dataclass
import json
from hashlib import sha256
from typing import Any,Literal

from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import Engine,select,text

from corpus_structure.core.method import UnitRef,UnitResult,ObservationDraft
from corpus_structure.core.vocab import TaskUnitType,ObservationKind,ObservationOutcome
from .identity import canonical_bytes
from .metadata import table
from .operations import (OperationDescriptor,binding_of,create_run,create_task,record_method,
                         claim_tasks,complete_unit_result,seal_cut,end_source_run)
from .source_views import load_source_view,store_region_artifact


class NativeRequestConfig(BaseModel):
    model_config=ConfigDict(frozen=True,extra='forbid')
    source_view_id:int=Field(gt=0)
    native_product:dict[str,Any]
    projection_digest:str
    recipe_digest:str
    demand:Literal['lexical','structure','syntax','interpretation','symbolic','assessment','render']
    pointer:str|None=None
    question:str|None=None
    predicate:str|None=None
    seconds:float=Field(default=2,gt=0)
    region_index:int|None=Field(default=None,ge=0)
    scale:float=Field(default=2,gt=0,le=8)
    domain_rules:tuple[dict[str,Any],...]=()


@dataclass(frozen=True)
class NativeRequestResult:
    run_id:int
    task_id:int
    cut_id:int|None
    status:str
    source_view_id:int
    product_digest:str|None=None
    artifact_digest:str|None=None
    result:dict[str,Any]|None=None
    error:str|None=None


def request_source_view(engine:Engine,*,source_run_id:int,source_view_id:int,demand:str,
                        code_commit:str,pointer:str|None=None,question:str|None=None,
                        predicate:str|None=None,seconds:float=2,region_index:int|None=None,
                        scale:float=2,holder:str='native-source-request')->NativeRequestResult:
    from .releases import open_release
    from .contracts import require_bound_operation
    from .observations import source_python
    from .claim_lifetime import maintained_claims
    from corpus_structure.methods.math.native import NativeAnalysisPayload,native_request_analysis

    runs,tasks=table('ops.run'),table('ops.task')
    with engine.begin() as conn:
        origin=conn.execute(select(runs).where(runs.c.id==source_run_id)).mappings().one()
        prepared=open_release(conn,origin['release_id'])
        require_bound_operation(prepared,'request_native_source')
        if not conn.execute(select(table('ops.run_source_view').c.source_view_id).where(
                table('ops.run_source_view').c.run_id==source_run_id,
                table('ops.run_source_view').c.source_view_id==source_view_id)).scalar_one_or_none():
            raise ValueError('native source request requires an explicitly selected source view')
        view=load_source_view(conn,source_view_id)
        source_binding=binding_of(conn,source_run_id)
        archived=json.loads(source_binding.dependencies)
        rules=[v.get('parameters',{}).get('math',{}).get('native_domain_rules',[]) for v in archived.get('operations',{}).values() if v.get('parameters',{}).get('math',{}).get('native_domain_rules')]
        if rules and any(canonical_bytes(r)!=canonical_bytes(rules[0]) for r in rules[1:]):
            raise ValueError('native source request has competing archived domain-rule contexts')
        domain_rules=tuple(rules[0]) if rules else ()
        config=NativeRequestConfig(source_view_id=source_view_id,native_product=view.ref.native_product.values(),
            projection_digest=view.ref.projection_digest,recipe_digest=view.ref.recipe_digest,demand=demand,
            pointer=pointer,question=question,predicate=predicate,seconds=seconds,region_index=region_index,scale=scale,domain_rules=domain_rules)
        if demand=='render' and (pointer is None or region_index is None):
            raise ValueError('render requires native occurrence and region index')
        if demand=='assessment' and not question:
            raise ValueError('assessment requires a named question')
        params=config.model_dump(mode='json')
        digest=sha256(canonical_bytes(params)).hexdigest()
        method=OperationDescriptor('native.source_request','1','normalize','deterministic',TaskUnitType.SOURCE_VIEW,NativeRequestConfig)
        source_binding=binding_of(conn,source_run_id)
        run_id=create_run(conn,project_id=origin['project_id'],binding=source_binding,kind='slice',options={'native_request':params},code_commit=code_commit)
        conn.execute(text('SELECT ops.select_source_view(:run,:source,:view)'),dict(run=run_id,source=source_run_id,view=source_view_id))
        config_id=record_method(conn,method,'request',params,digest,prepared=prepared)
        task_id=create_task(conn,run_id=run_id,config_id=config_id,stage='parsing',unit_type='source_view',
                            unit_id=source_view_id,unit_key='native-request:'+digest,input_hash=digest)
        reused=conn.execute(select(tasks.c.reused_task_id).where(tasks.c.id==task_id)).scalar_one()
        if reused is not None:
            body=conn.execute(select(table('ops.task_result').c.body).where(table('ops.task_result').c.task_id==reused)).scalar_one()
            raw=body.get('observations',[])
            result=source_python(raw[0]['payload']) if raw else None
            artifact=conn.execute(select(table('ops.native_region_artifact').c.artifact_digest).where(table('ops.native_region_artifact').c.task_id==reused)).scalar_one_or_none()
            cut=seal_cut(conn,run_id,'native-request-source',final=True)
            return NativeRequestResult(run_id,task_id,cut,'source_ready',source_view_id,
                sha256(canonical_bytes(body)).hexdigest(),artifact,result)
        claim=claim_tasks(conn,run_id=run_id,config_id=config_id,holder=holder)[0]
        region=None; original=None
        if demand=='render':
            regions=table('kb.native_document_region')
            region=dict(conn.execute(select(regions).where(regions.c.task_id==view.ref.native_product.task_id,
                regions.c.product_key==view.ref.native_product.product_key,regions.c.pointer==pointer,
                regions.c.region_index==region_index)).mappings().one())
            build,artifact=table('ops.source_build'),table('kb.source_artifact')
            original=bytes(conn.execute(select(artifact.c.content).join(build,build.c.artifact_digest==artifact.c.artifact_digest).where(build.c.task_id==view.ref.native_product.task_id)).scalar_one())
    try:
        with maintained_claims(engine,(claim,),holder):
            artifact_bytes=None
            if demand=='render':
                from corpus_structure.serve.native_regions import render_pdf_region
                assert original is not None and region is not None
                artifact_bytes=render_pdf_region(original,region,scale=scale)
                analysis=None
            else:
                analysis=native_request_analysis(view,prepared,demand,pointer,question,predicate,seconds,domain_rules=domain_rules)
        observations=() if analysis is None else (ObservationDraft(kind=ObservationKind.FORMULA,
            payload=analysis,payload_class=NativeAnalysisPayload,payload_version='1',source_view_id=source_view_id,native_pointer=pointer),)
        result=UnitResult(ref=UnitRef(TaskUnitType.SOURCE_VIEW,source_view_id,'native-request:'+digest),
                          outcome=ObservationOutcome.PRODUCED if observations else ObservationOutcome.EMPTY,observations=observations)
        with engine.begin() as conn:
            artifact_digest=None
            if artifact_bytes is not None:
                selection=dict(view.ref.native_product.values(),pointer=pointer,region_index=region_index)
                recipe=canonical_bytes(dict(recipe='pdf-region-render-v1',selection=selection,scale=scale))
                artifact_digest=store_region_artifact(conn,task_id=task_id,attempt=claim.attempt,holder=holder,selection=selection,recipe_bytes=recipe,content=artifact_bytes)
            complete_unit_result(conn,task_id=task_id,attempt=claim.attempt,holder=holder,prepared=prepared,
                                 result=result,method=method,configuration_hash=digest,source=view.ref.key)
            cut=seal_cut(conn,run_id,'native-request-source',final=True)
            body=conn.execute(select(table('ops.task_result').c.body).where(table('ops.task_result').c.task_id==task_id)).scalar_one()
        return NativeRequestResult(run_id,task_id,cut,'source_ready',source_view_id,sha256(canonical_bytes(body)).hexdigest(),artifact_digest,
                                   analysis.model_dump(mode='json') if analysis is not None else None)
    except BaseException as error:
        with engine.begin() as conn:
            end_source_run(conn,run_id,failure={'message':str(error),'exception':type(error).__name__})
        raise
