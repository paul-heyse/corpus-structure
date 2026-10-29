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
                       configurations:Mapping[str,str]|None=None,guideline:str="",fresh:Any=())->BoundRunReport:
    """Run the current source graph; hand its immutable cut to consolidation/proposal owners.

    This result establishes source preparation only. It does not report grading, inference,
    or whole-run completion. Source work never chooses an unbound latest interpretation.
    """
    from corpus_structure.orchestrate.runs import code_commit
    from corpus_structure.semantic.identity import canonical_bytes
    from hashlib import sha256
    if binding.release_id!=prepared.release_id:raise OperationConflict('run release differs from prepared interpretation')
    registry=registry.bind_release(prepared)
    configurations=dict(configurations or {})
    configs={}
    for _,steps in graph.stages:
        for step in steps:
            method,_,default=step.config.partition('/')
            name=configurations.get(method,default or 'default')
            configs[method]=registry.resolve(method,name)
    fresh=tuple(sorted(set(fresh)))
    unknown=set(fresh)-{method.name for method in registry.methods()}
    if unknown:raise OperationConflict('fresh names unregistered methods: '+', '.join(sorted(unknown)))
    agent_configs={}
    from corpus_structure.core.method import config_references,PackSection,ArtifactRef
    for method_name,config_name in registry.named():
        if method_name!='agent.opus':continue
        config=registry.overlay(method_name,config_name)
        raw=config.model_dump(mode='json')
        markers=config_references(type(config))
        for path,marker in markers.items():
            if isinstance(marker,PackSection):
                if len(path)!=1:raise OperationConflict('nested agent operation sections are unsupported')
                raw[path[0]]=registry.file.sections[marker.name]
        values=type(config).model_validate(raw).model_dump(mode='json')
        for path,marker in markers.items():
            if isinstance(marker,ArtifactRef):values.pop(path[0],None)
        agent_configs[config_name]=values
    with engine.begin() as conn:
        d=table('kb.document')
        docs=conn.execute(select(d).where(d.c.project_id==project_id).order_by(d.c.key)).mappings().all()
        if not docs:raise OperationConflict('bound project has no registered source documents')
        import json
        from importlib.metadata import version
        library_names=set()
        if 'ingest.html' in configs:library_names.update(('regex','spacy','en-core-web-sm','html5lib','lxml','cssselect2'))
        if set(configs)&{'extract.math','normalize.formula'}:library_names.add('lark')
        if 'resolve.symbol_scope' in configs:library_names.update(('spacy','en-core-web-sm'))
        if graph.policy_propose:library_names.update(('rapidfuzz','regex','rule-engine'))
        dependency_manifest={
            'parent':json.loads(binding.dependencies),
            'libraries':{name:version(name) for name in sorted(library_names)},
            'source_documents':[{'key':d['key'],'uri':d['source_uri'],'content_hash':d['content_hash'],'metadata':d['meta']} for d in docs],
            'operations':{name:{'version':registry.method(name).version,'family':str(registry.method(name).family),'tier':str(registry.method(name).tier),'confidence_source':str(registry.method(name).confidence_source) if registry.method(name).confidence_source is not None else None,'configuration_hash':config.config_hash,'parameters':dict(config.params)} for name,config in configs.items()},
            'guideline':guideline,
            'agent_configurations':agent_configs,
        }
        binding=OperationBinding(binding.release_id,binding.input_realization_id,binding.input_revision,canonical_bytes(dependency_manifest))
        options={'corpus':{'documents':[d['key'] for d in docs]},'configs':{m:c.config_hash for m,c in configs.items()},'agent_configs':agent_configs,'fresh':list(fresh)}
        rid=create_run(conn,project_id=project_id,binding=binding,kind='full',options=options,code_commit=code_commit(),phase=phase,guideline=guideline)
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
                        task_id=create_task(conn,run_id=rid,config_id=cid,stage=str(stage),unit_type=str(ref.unit_type),unit_id=ref.unit_id,unit_key=ref.unit_key,input_hash=ih,packet_hash=digest.packet_hash,fresh=name in fresh)
                        if ref.unit_type==TaskUnitType.DOCUMENT and ref.unit_id is not None:
                            task_table=table('ops.task')
                            if conn.execute(select(task_table.c.status).where(task_table.c.id==task_id)).scalar_one()=='reused':
                                from corpus_structure.semantic.operations import read_original
                                read_original(conn,ref.unit_id)
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
    except BaseException as exc:
        from asyncio import CancelledError
        from corpus_structure.semantic.operations import end_source_run
        failure=None if isinstance(exc,(KeyboardInterrupt,CancelledError)) else {'message':str(exc),'exception':type(exc).__name__}
        try:
            with engine.begin() as conn:end_source_run(conn,rid,failure=failure)
        except BaseException as cleanup_error:
            exc.add_note(f"source run cleanup failed: {cleanup_error}")
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


def _packet_for_unit(conn:Any,run_id:int,prepared:Any,ref:Any,configuration:Mapping[str,Any]):
    """Shared queue/serve preparation including recorded M13 standing context."""
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.core.locators import LocatorIndex
    from corpus_structure.methods.llm.packet import unit_inputs
    from corpus_structure.semantic.proposals import ProposalFrame,ProposalSentence,proposal_packet
    view=run_view(conn,run_id,prepared)
    unit=_unit(conn,view,ref)
    if unit.rendition_id is None or ref.unit_key is None:
        raise OperationConflict('an agent proposal requires a located source unit')
    raw_math=configuration.get('math',{})
    macros={name:MacroDef(body=body) for name,body in raw_math.get('macros',{}).items()}
    inputs=unit_inputs(view.reader,rendition_id=unit.rendition_id,document_id=unit.document_id,
        unit_key=ref.unit_key,reference_run_id=None,pack_macros=macros)
    rendered=inputs.packet(configuration.get('packet_cap_chars',18000))
    index=LocatorIndex(inputs.content,inputs.page)
    sentences=[]
    for item in rendered.sentences:
        segment=index.resolve(item.locator)
        if inputs.content.canonical_text[segment.start:segment.end]!=item.text:
            raise OperationConflict('packet sentence differs from source frame')
        sentences.append(ProposalSentence(item.id,item.locator,segment.start,segment.end))
    return proposal_packet(prepared,ProposalFrame(ref.unit_key,inputs.content.canonical_text,tuple(sentences)),
        guideline=view.reader.guideline(),configuration=configuration,macros=inputs.macros)


def agent_packet(conn:Any,run_id:int,task_id:int,prepared:Any):
    """Rebuild exactly the packet hashed by queue_agent; no active release lookup."""
    t,c=table('ops.task'),table('ops.method_config')
    row=conn.execute(select(t,c.c.params).join(c,t.c.method_config_id==c.c.id).where(t.c.id==task_id,t.c.run_id==run_id)).mappings().one()
    ref=UnitRef(TaskUnitType(row['unit_type']),row['unit_id'],row['unit_key'])
    packet=_packet_for_unit(conn,run_id,prepared,ref,row['params'])
    if row['packet_hash']!=packet.hash:raise OperationConflict('recorded agent packet changed')
    return packet


def queue_agent(conn:Any,*,run_id:int,prepared:Any,configuration:Mapping[str,Any],
                units:Any,configuration_name:str='extract')->list[int]:
    """Queue policy-selected source units under the same packet definition used by MCP."""
    from hashlib import sha256
    from corpus_structure.semantic.operations import OperationDescriptor
    from corpus_structure.semantic.proposals import SEMANTIC_AGENT_VERSION
    if not configuration.get('model'):raise ValueError('agent configuration declares its model')
    method=OperationDescriptor("agent.opus",SEMANTIC_AGENT_VERSION,"agent","agent","agent")
    config_hash='configuration:'+sha256(canonical_bytes([method.name,method.version,dict(configuration)])).hexdigest()
    config_id=record_method(conn,method,configuration_name,configuration,config_hash)
    view=run_view(conn,run_id,prepared)
    binding=view.binding
    snapshot=view.options.get('agent_configs',{})
    if not isinstance(snapshot,dict) or configuration_name not in snapshot or canonical_bytes(snapshot[configuration_name])!=canonical_bytes(dict(configuration)):
        raise OperationConflict('agent configuration differs from immutable run snapshot')
    fresh_names=view.options.get('fresh',[])
    if not isinstance(fresh_names,list) or any(not isinstance(name,str) for name in fresh_names):
        raise OperationConflict('run fresh selector is not a string list')
    tasks=[]
    for ref in units:
        packet=_packet_for_unit(conn,run_id,prepared,ref,configuration)
        digest=sha256(canonical_bytes([binding.release_id,binding.input_realization_id,binding.input_revision,
            binding.dependency_digest,method.version,config_hash,packet.hash])).hexdigest()
        tasks.append(create_task(conn,run_id=run_id,config_id=config_id,stage='propose',unit_type=str(ref.unit_type),unit_id=ref.unit_id,unit_key=ref.unit_key,input_hash=digest,packet_hash=packet.hash,agent=True,fresh='agent.opus' in fresh_names))
    return tasks
