"""Actual automatic definition RUN execution with native leases and retained source frames."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from sqlalchemy import text
from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.definition_applicability import DefinitionApplicabilityConfig, DefinitionApplicabilityMethod
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId,RealizationId,ReleaseId
from corpus_structure.semantic.authored_sql import has_authored_sql,analyze_archived_sql,admit_archived_sql
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import OperationBinding,seal_cut
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
PROJECT='pce-statistics-structural'

def main(release,attempt):
    settings=Settings()
    frozen=json.loads((HERE/'raw/production-input-002.json').read_bytes())
    old=json.loads((HERE.parent/'2026-11-05_pce-local-capabilities/raw/parser-corpus-003-configuration.json').read_bytes())['configs']['extract.m1_candidates']
    profile=M1Config.model_validate(old).profile()
    with open_runtime_engine(settings,'automatic-definition-admit',purpose='admit') as engine,engine.begin() as conn:
        prepared=open_release(conn,release)
        if has_authored_sql(prepared):
            with open_runtime_engine(settings,'automatic-definition-sql',purpose='read') as read,read.connect() as source:
                analyzed=analyze_archived_sql(source,release)
            admit_archived_sql(conn,release,analyzed=analyzed)
        admit_release(prepared,connection=conn)
    outcomes=[]
    with open_runtime_engine(settings,'automatic-definition-run',purpose='write') as engine:
        realization='pce-auto-input:'+release
        with engine.begin() as conn:
            initialize_source_project(conn,project_id=ProjectId(PROJECT),release_id=ReleaseId(release),realization_id=RealizationId(realization),projection_context=prepared)
            before=dict(conn.execute(text('SELECT * FROM data.project WHERE project_id=:p'),{'p':PROJECT}).mappings().one())
        for label,key,usage in [('normal','inputs','usage_id'),('mean','mean_inputs','mean_usage_id')]:
            inputs=StructuralInput.model_validate(frozen[key])
            cfg=DefinitionApplicabilityConfig(inputs=inputs,structural_input_digest=inputs.identity,usage_id=frozen[usage],target_ids=tuple(frozen['target_ids']),profile=profile)
            method=DefinitionApplicabilityMethod()
            registry=MethodRegistry((method,),MethodsFile(configs={method.name:{'actual':cfg.model_dump(mode='json',exclude_none=True)}}))
            graph=Graph(((Stage.LINK,(Step(method.name+'/actual'),)),))
            result=run_source_methods(engine,project_id=PROJECT,prepared=prepared,binding=OperationBinding(release,realization,0,canonical_bytes({'frozen_source':sha256((HERE/'raw/production-input-002.json').read_bytes()).hexdigest(),'automatic_case':label,'scope':'no supplied readings or protected feedback'})),registry=registry,graph=graph,method_settings=MethodSettings(data_dir=settings.paths.data_dir,model_cache=settings.paths.model_cache),domain='statistics')
            with engine.begin() as conn:
                cut=seal_cut(conn,result.run_id,'automatic-definition-final',final=True)
            completed=consolidate_cut(engine,cut,f'pce-auto-result:{result.run_id}')
            with engine.connect() as conn:
                tasks=list(conn.execute(text('SELECT t.id,t.status,r.body FROM ops.task t JOIN ops.task_result r ON r.task_id=coalesce(t.reused_task_id,t.id) WHERE t.run_id=:r ORDER BY t.id'),{'r':result.run_id}).mappings())
            outcomes.append({'label':label,'run_id':result.run_id,'cut_id':cut,'realization_id':completed.realization_id,'tasks':[dict(row) for row in tasks],'worker_settled':method._worker is None})
        with engine.connect() as conn:
            after=dict(conn.execute(text('SELECT * FROM data.project WHERE project_id=:p'),{'p':PROJECT}).mappings().one())
        assert before==after,'automatic definition changed defaults'
    payload={'outcome':'passed','scope':'actual registered leased automatic E5/PostgreSQL/GLiNER RUN producer; independent semantic quality separate','release_id':release,'defaults_activated':False,'cases':outcomes,'source_frame':'production-input-002.json','protected_reference_answers_consumed':False,'supplied_applicability_readings':False,'project_before':before,'project_after':after}
    with (HERE/f'raw/automatic-runs-{attempt}.json').open('xb') as out:out.write(canonical_bytes(payload)+b'\n')
    print(json.dumps({'outcome':'passed','runs':[(r['label'],r['run_id'],r['cut_id']) for r in outcomes],'release_id':release}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--release',required=True);parser.add_argument('--attempt',default='001');args=parser.parse_args();main(args.release,args.attempt)
