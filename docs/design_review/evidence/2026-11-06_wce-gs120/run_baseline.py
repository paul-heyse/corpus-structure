"""Actual current registered generic M1 and located-definition production on shared GS120.

Retained native adoption does not rerun PDF/recognition. New annotation/source identities are
truthfully recorded; definition extraction binds the authenticated original annotation run.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import yaml
from sqlalchemy import select,text
from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.ingest.pdf_methods import IngestPdf
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.methods.m1_source import M1Candidates
from corpus_structure.methods.definition_applicability import DefinitionComponentsMethod
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.orchestrate.registry import MethodRegistry,MethodsFile
from corpus_structure.orchestrate.runner import Graph,Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding,seal_cut
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput,ExternalSourceRef
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId,ReleaseId,RealizationId
from corpus_structure.serve.contributions import ContributionRequest,serve_contributions,export_contribution_selection
from corpus_structure.serve.structural_products import StructuralRequest,serve_structural_products
from corpus_structure.settings import Settings
HERE=Path(__file__).resolve().parent
PROJECT='wce-gs120-method-development-20261106'
def retain(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:f.write(canonical_bytes(value)+b'\n')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('attempt');parser.add_argument('--only-cut');args=parser.parse_args()
    output=HERE/('baseline'+args.attempt);output.mkdir(exist_ok=False)
    packet=json.loads((HERE/'source-packets/source-packet.json').read_bytes());manifest=packet['source_manifest']
    declared=yaml.safe_load((DOMAINS/'statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates'];m1=declared['witnessed']
    settings=Settings();reports=[]
    try:
        with open_runtime_engine(settings,'gs120-baseline-input',purpose='read') as engine,read_snapshot(engine) as conn:
            prepared=open_release(conn,packet['completed_result']['release_id'])
            annotation_ids=conn.execute(text("SELECT t.id FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id JOIN ops.method m ON m.id=c.method_id WHERE t.run_id=:run AND m.name='extract.m1_annotations' ORDER BY t.id"),dict(run=packet['run_id'])).scalars().all()
        for cut_source in [dict(file='gs120-all120-pages',sha256=manifest['parent_sha256'])]:
            rows=[row for row in packet['views'] if row['analysis_eligible'] and row['chars']]
            if not rows:raise ValueError('selected native input has no analysis-eligible source view')
            ids={row['id'] for row in rows};source_values=[s for s in packet['sources'] if s['source_view_id'] in ids]
            # Let the current declared model parse/authenticate the source manifest, without aliases.
            passages=[p for p in packet['passages'] if p['passage_id'] in {'gs120-source-'+str(i) for i in ids}]
            inputs=StructuralInput.model_validate(dict(question='Construct source-grounded definitions and explanations',scope='grinstead-snell-physical191-310',inventory_id='gs120:'+cut_source['sha256'],policy_id='located-definition-1',sources=source_values,passages=passages,dependencies=tuple(dict.fromkeys([*('native:'+str(r['native_task_id']) for r in rows),*('annotation:'+str(i) for i in annotation_ids)]))))
            profile={key:declared['default'][key] for key in ('snapshot','checkpoint','revision','artifact_hashes')}
            config=dict(inputs=inputs.model_dump(mode='json'),structural_input_digest=inputs.identity,target_ids=[p.passage_id for p in inputs.passages],profile=profile,annotation_rules=m1['annotation_rules'])
            first=rows[0];root=output/Path(cut_source['file']).stem;root.mkdir()
            retain(root/'configuration.json',dict(m1=m1,definition=config,native_input=cut_source))
            candidate=M1Candidates();definition=DefinitionComponentsMethod()
            registry=MethodRegistry((M1Annotations(),candidate,definition),MethodsFile(configs={M1Annotations.name:{'default':{}},candidate.name:{'witnessed':m1},definition.name:{'default':config}}))
            realization='gs120-baseline:'+args.attempt+':'+cut_source['sha256']+':'+prepared.release_id
            with open_runtime_engine(settings,'gs120-baseline-register',purpose='write') as engine,engine.begin() as conn:initialize_source_project(conn,project_id=ProjectId(PROJECT),release_id=ReleaseId(prepared.release_id),realization_id=RealizationId(realization),projection_context=prepared)
            with open_runtime_engine(settings,'gs120-baseline-run',purpose='write') as engine:
                with engine.connect() as conn:
                    revision=conn.scalar(select(table('data.realization').c.data_revision).where(table('data.realization').c.realization_id==realization))
                    docs=conn.execute(select(table('kb.document')).where(table('kb.document').c.project_id==PROJECT)).mappings().all();corpus_record,_=records(docs,{},slice=None,scope=None,corpus=None)
                result=run_source_methods(engine,project_id=PROJECT,prepared=prepared,binding=OperationBinding(prepared.release_id,realization,revision,canonical_bytes(dict(shared_source=manifest['parent_sha256'],cut=cut_source['sha256'],baseline=args.attempt))),registry=registry,graph=Graph(((Stage.EXTRACT,(Step(M1Annotations.name+'/default'),Step(candidate.name+'/witnessed',upstream=(M1Annotations.name,)),Step(definition.name+'/default'))),),policy_propose=False),method_settings=MethodSettings(data_dir=root/'data',model_cache=Path.home()/'.cache/docling/models'),guideline=(DOMAINS/'statistics/m1-guideline.md').read_text(),corpus_record=corpus_record,policy_source=None,kind='full',selected_sources=tuple(ExternalSourceRef.model_validate(v) for v in source_values))
                retain(root/'run.json',result.model_dump(mode='json'))
                if result.status!='source_ready':raise ValueError('baseline run did not reach source readiness; retained failure')
                with engine.begin() as conn:cut=seal_cut(conn,result.run_id,'gs120-baseline-final',final=True)
                consolidate_cut(engine,cut,'gs120-baseline:'+str(result.run_id))
                with read_snapshot(engine) as conn:
                    task,result_table=table('ops.task'),table('ops.task_result')
                    bodies=[dict(r) for r in conn.execute(select(task.c.id,task.c.unit_type,result_table.c.body).join(result_table,result_table.c.task_id==task.c.id).where(task.c.run_id==result.run_id)).mappings()]
                    retain(root/'raw-task-envelopes.json',bodies)
                    request=ContributionRequest(run_id=result.run_id,limit=1000,page_bytes=8_000_000)
                    pages=[]
                    while True:
                        page=serve_contributions(conn,request);pages.append(page.model_dump(mode='json'))
                        if page.next_cursor is None:break
                        request=request.model_copy(update={'cursor':page.next_cursor})
                    retain(root/'contributions.json',pages)
                    retain(root/'contribution-export.json',export_contribution_selection(conn,ContributionRequest(run_id=result.run_id),root/'contribution-export'))
                    structural=serve_structural_products(conn,StructuralRequest(run_id=result.run_id,kind='definition_components',max_bytes=8_000_000));retain(root/'structural-inspection.json',structural.model_dump(mode='json'))
            report=dict(cut_source=cut_source['file'],run_id=result.run_id,cut_id=cut,contributions=pages[0]['inventory_counts'],components=sum(len(r.definition_components.components) for r in structural.reports),standing='private_unassessed')
            reports.append(report);retain(root/'result.json',dict(outcome='passed',**report));print(json.dumps(report),flush=True)
        retain(output/'result.json',dict(outcome='passed',runs=reports,source_pages=120,scope='actual current registered generic M1/named/definition source construction; source first quantity and semantic quality unassessed'))
    except BaseException as error:
        retain(output/'failure.json',dict(outcome='failed',type=type(error).__name__,message=str(error),completed_runs=reports));raise
if __name__=='__main__':main()
