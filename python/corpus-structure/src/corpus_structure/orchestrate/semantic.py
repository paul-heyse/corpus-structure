"""The existing deterministic method graph on explicitly selected semantic run bindings."""
from __future__ import annotations
import logging
from typing import Any, Mapping
from pydantic import BaseModel
from sqlalchemy import select,update
from corpus_structure.core.method import MethodContext,UnitRef,UnitView
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (OperationBinding,OperationConflict,run_view,create_run,record_method,create_task,claim_tasks,complete_unit_result,seal_cut)


class BoundRunReport(BaseModel):
    run_id:int
    status:str
    release_id:str
    realization_id:str
    cut_id:int|None=None


def run_source_methods(engine:Any,*,project_id:str,prepared:Any,binding:OperationBinding,
                       registry:Any,graph:Any,method_settings:Any,phase:int=0,
                       configurations:Mapping[str,str]|None=None)->BoundRunReport:
    """Run the current source graph; hand its immutable cut to consolidation/proposal owners.

    This result establishes source preparation only. It does not report grading, inference,
    or whole-run completion. Source work never chooses an unbound latest interpretation.
    """
    from corpus_structure.orchestrate.runs import code_commit
    from corpus_structure.semantic.identity import canonical_bytes
    from hashlib import sha256
    if binding.release_id!=prepared.release_id:raise OperationConflict('run release differs from prepared interpretation')
    configurations=dict(configurations or {})
    configs={}
    for _,steps in graph.stages:
        for step in steps:
            method,_,default=step.config.partition('/')
            name=configurations.get(method,default or 'default')
            configs[method]=registry.resolve(method,name)
    with engine.begin() as conn:
        d=table('kb.document')
        docs=conn.execute(select(d).where(d.c.project_id==project_id).order_by(d.c.key)).mappings().all()
        if not docs:raise OperationConflict('bound project has no registered source documents')
        options={'corpus':{'documents':[d['key'] for d in docs]},'configs':{m:c.config_hash for m,c in configs.items()}}
        rid=create_run(conn,project_id=project_id,binding=binding,kind='full',options=options,code_commit=code_commit(),phase=phase)
        conn.execute(update(table('ops.run')).where(table('ops.run').c.id==rid).values(status='running'))
    holder=f'semantic-source:{rid}'
    try:
        for stage,steps in graph.stages:
            for step in steps:
                name=step.config.split('/',1)[0];method=registry.method(name);config=configs[name]
                with engine.begin() as conn:
                    cid=record_method(conn,method,config.name,config.params,config.config_hash)
                    view=run_view(conn,rid,prepared)
                    for ref in method.select(view,config.config):
                        unit=_unit(conn,view,ref)
                        digest=method.input_digest(unit,config.config)
                        ih=sha256(canonical_bytes([prepared.release_id,binding.input_realization_id,binding.input_revision,binding.dependency_digest,method.name,method.version,config.config_hash,digest.bytes.hex()])).hexdigest()
                        create_task(conn,run_id=rid,config_id=cid,stage=str(stage),unit_type=str(ref.unit_type),unit_id=ref.unit_id,unit_key=ref.unit_key,input_hash=ih,packet_hash=digest.packet_hash)
                while True:
                    with engine.begin() as conn:claimed=claim_tasks(conn,run_id=rid,config_id=cid,holder=holder,limit=method.resources.batch_size)
                    if not claimed:break
                    with engine.connect() as conn:
                        view=run_view(conn,rid,prepared)
                        units=[_unit(conn,view,UnitRef(TaskUnitType(t['unit_type']),t['unit_id'],t['unit_key'])) for t in claimed]
                        results=method.run(units,config.config,MethodContext(view,view.reader,method_settings,logging.getLogger(method.name)))
                        conn.rollback()
                    for task,result in zip(claimed,results,strict=True):
                        with engine.begin() as conn:
                            complete_unit_result(conn,task_id=task['id'],attempt=task['attempt'],holder=holder,prepared=prepared,result=result,method=method,configuration_hash=config.config_hash,source=result.ref.unit_key or 'run')
                        if result.error is not None:raise OperationConflict(result.error)
        with engine.begin() as conn:cut=seal_cut(conn,rid,'source-ready')
        return BoundRunReport(run_id=rid,status='source_ready',release_id=prepared.release_id,realization_id=binding.input_realization_id,cut_id=cut)
    except BaseException:
        with engine.begin() as conn:conn.execute(update(table('ops.run')).where(table('ops.run').c.id==rid).values(status='failed'))
        raise


def _unit(conn:Any,view:Any,ref:Any)->UnitView:
    if ref.unit_type==TaskUnitType.DOCUMENT:return UnitView(ref,view,document_id=ref.unit_id)
    if ref.unit_type==TaskUnitType.RENDITION:
        r=table('kb.rendition');doc=conn.execute(select(r.c.document_id).where(r.c.id==ref.unit_id)).scalar_one()
        return UnitView(ref,view,document_id=doc,rendition_id=ref.unit_id)
    if ref.unit_type==TaskUnitType.SEGMENT:
        s=table('kb.segment');r=table('kb.rendition')
        row=conn.execute(select(s.c.rendition_id,r.c.document_id).join(r,s.c.rendition_id==r.c.id).where(s.c.id==ref.unit_id)).one()
        return UnitView(ref,view,document_id=row.document_id,rendition_id=row.rendition_id)
    return UnitView(ref,view)
