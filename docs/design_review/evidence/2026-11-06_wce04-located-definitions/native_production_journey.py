"""Registered actual definition producer over authenticated retained corpus sources."""
from pathlib import Path
import argparse
import json

import yaml
from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.definition_applicability import DefinitionComponentsMethod
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, ReleaseId, RealizationId
from corpus_structure.semantic.authored_sql import admit_archived_sql, analyze_archived_sql, has_authored_sql
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, seal_cut
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.regeneration import acquire_pack, compose_pack_inputs
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_sources import StructuralPassageSelection, prepare_structural_sources
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.serve.structural_products import StructuralRequest, serve_structural_products
from corpus_structure.settings import Settings


def retain(path, value):
    path.write_bytes(canonical_bytes(value)+b'\n')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
    output=Path(__file__).parent/('native'+args.attempt);output.mkdir(exist_ok=False)
    settings=Settings()
    try:
        with open_runtime_engine(settings,'wce-definition-source',purpose='read') as engine:
            sources=prepare_structural_sources(engine,(StructuralPassageSelection(run_id=113,source_view_id=53,passage_id='normal-native-53',start=0,end=5684,scope='wce-statistics-normal-002'),))
        inputs=StructuralInput(question='Locate definition components',scope='wce-statistics-normal-002',inventory_id='normal-native-53',policy_id='located-definition-1',sources=sources.sources,passages=sources.passages,dependencies=('native:260','annotation:285'))
        declared=yaml.safe_load((DOMAINS/'statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates']
        baseline=declared['default']
        profile={key:baseline[key] for key in ('snapshot','checkpoint','revision','artifact_hashes')}
        config=dict(inputs=inputs.model_dump(mode='json'),structural_input_digest=inputs.identity,target_ids=['normal-native-53'],profile=profile,annotation_rules=declared['witnessed']['annotation_rules'])
        retain(output/'configuration.json',config)
        bundle,dependencies,profile_context=compose_pack_inputs((acquire_pack(DOMAINS/'statistics'),))
        prepared=prepare_release(bundle,dependencies,profile_context)
        retain(output/'release.json',{'release_id':prepared.release_id})
        with open_runtime_engine(settings,'wce-definition-release',purpose='admit') as engine,engine.begin() as conn:
            persist_release(conn,bundle,dependencies,profile_context,prepared)
        analyzed=None
        if has_authored_sql(prepared):
            with open_runtime_engine(settings,'wce-definition-sql',purpose='read') as engine,engine.connect() as conn:
                analyzed=analyze_archived_sql(conn,prepared.release_id)
        with open_runtime_engine(settings,'wce-definition-admit',purpose='admit') as engine,engine.begin() as conn:
            if analyzed:
                admit_archived_sql(conn,prepared.release_id,analyzed=analyzed)
            admit_release(prepared,connection=conn)
        method=DefinitionComponentsMethod()
        registry=MethodRegistry((method,),MethodsFile(configs={method.name:{'default':config}}))
        project='wce04-normal-definitions-20261106'
        realization='wce04-normal-input:'+args.attempt+':'+prepared.release_id
        with open_runtime_engine(settings,'wce-definition-project',purpose='write') as engine,engine.begin() as conn:
            initialize_source_project(conn,project_id=ProjectId(project),release_id=ReleaseId(prepared.release_id),realization_id=RealizationId(realization),projection_context=prepared)
        with open_runtime_engine(settings,'wce-definition-production',purpose='write') as engine:
            with engine.connect() as conn:
                revision=conn.scalar(select(table('data.realization').c.data_revision).where(table('data.realization').c.release_id==prepared.release_id,table('data.realization').c.realization_id==realization))
            result=run_source_methods(engine,project_id=project,prepared=prepared,binding=OperationBinding(prepared.release_id,realization,revision,canonical_bytes({'structural_input':inputs.identity})),registry=registry,graph=Graph(((Stage.EXTRACT,(Step(method.name+'/default'),)),),policy_propose=False),method_settings=MethodSettings(data_dir=output/'data',model_cache=Path.home()/'.cache/docling/models'),guideline='Retain source-grounded definition components; no scientific-truth claim.',kind='full')
            retain(output/'run.json',result.model_dump(mode='json'))
            if result.status!='source_ready':
                raise ValueError('registered definition producer did not reach source_ready')
            with engine.begin() as conn:
                cut=seal_cut(conn,result.run_id,'wce04-definition-components-final',final=True)
        with open_runtime_engine(settings,'wce-definition-consolidate',purpose='write') as engine:
            consolidate_cut(engine,cut,'wce04-normal-result:'+str(result.run_id))
        with open_runtime_engine(settings,'wce-definition-read',purpose='read') as engine,read_snapshot(engine) as conn:
            page=serve_structural_products(conn,StructuralRequest(run_id=result.run_id,kind='definition_components'))
            retain(output/'inspection.json',page.model_dump(mode='json'))
            task=table('ops.task');runs=table('ops.run')
            details=tuple(dict(r) for r in conn.execute(select(task.c.id,task.c.release_id,runs.c.runtime_id).join(runs,runs.c.id==task.c.run_id).where(task.c.id.in_(page.task_ids))).mappings())
            retain(output/'origin-tasks.json',details)
        retain(output/'result.json',{'outcome':'passed','run_id':result.run_id,'cut_id':cut,'release_id':prepared.release_id,'reports':len(page.reports),'component_count':sum(len(r.definition_components.components) for r in page.reports),'scope':'actual registered corpus producer, provider, native retention, completed ordinary read; independent assessment/publication not_run'})
        print((output/'result.json').read_text())
    except BaseException as error:
        retain(output/'failure.json',{'outcome':'failed','type':type(error).__name__,'message':str(error)})
        raise


if __name__=='__main__':
    main()
