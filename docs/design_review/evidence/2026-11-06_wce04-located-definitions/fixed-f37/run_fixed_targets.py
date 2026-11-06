"""Current registered local producers on the exposed F37 exact target windows.

Original six-view source text authenticates each target. No old classifier or
historical semantic reader executes; recorded51/52 are immutable comparison data.
"""
from __future__ import annotations

import json
import argparse
from collections import Counter
from hashlib import sha256
from pathlib import Path

import yaml
from sqlalchemy import select,text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.definition_applicability import DefinitionComponentsMethod
from corpus_structure.orchestrate.registry import MethodRegistry,MethodsFile
from corpus_structure.orchestrate.runner import Graph,Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId,ReleaseId,RealizationId
from corpus_structure.semantic.authored_sql import admit_archived_sql,analyze_archived_sql,has_authored_sql
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding,seal_cut
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.regeneration import acquire_pack,compose_pack_inputs
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import ExternalSourceRef,StructuralInput,StructuralPassage
from corpus_structure.serve.structural_products import StructuralRequest,serve_structural_products
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[5]
SOURCE=ROOT/'docs/design_review/evidence/2026-11-06_wce-candidate-foundation/raw/source-author-input-001.json'
OLD=ROOT/'docs/design_review/evidence/2026-11-05_pce-structural-products/raw'


def retain(name,value):
    (HERE/name).write_bytes(canonical_bytes(value)+b'\n')


def main():
    global HERE
    parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
    HERE=HERE/args.attempt;HERE.mkdir(exist_ok=False)
    packet=json.loads(SOURCE.read_bytes())
    original=json.loads((OLD/'production-input-002.json').read_bytes())
    baseline=json.loads((OLD/'automatic-assessment-input-005.json').read_bytes())
    judgments=json.loads((OLD/'independent-automatic-C-001.json').read_bytes())
    sources=tuple(ExternalSourceRef.model_validate(v) for v in packet['sources'])
    whole={v['source_ref']:v for v in packet['passages']}
    passages=tuple(StructuralPassage.model_validate(v) for v in original['inputs']['passages'])
    targets=tuple(original['target_ids'])
    for p in passages:
        reference=whole[p.source_ref]
        assert reference['text'][p.start-reference['start']:p.end-reference['start']]==p.text
    inputs=StructuralInput(question='Target-local definition/role/attachment extraction on original fixed F37 targets; usage applicability is a separate operation.',scope=original['inputs']['scope'],inventory_id='fixed-f37-targets:'+sha256(canonical_bytes(targets)).hexdigest(),policy_id='witnessed-target-local-definition-1',sources=sources,passages=passages,dependencies=tuple('source:'+s.identity for s in sources),coverage_limits=tuple(original['inputs']['coverage_limits']))
    freeze=dict(source_packet_sha256=sha256(SOURCE.read_bytes()).hexdigest(),baseline_inputs_sha256=sha256((OLD/'production-input-002.json').read_bytes()).hexdigest(),baseline_outputs_sha256=sha256((OLD/'automatic-assessment-input-005.json').read_bytes()).hexdigest(),baseline_judgments_sha256=sha256((OLD/'independent-automatic-C-001.json').read_bytes()).hexdigest(),physical_source_views=len(sources),fixed_target_windows=len(targets),selected_target_characters=sum(len(p.text) for p in passages if p.passage_id in targets),inputs=inputs.model_dump(mode='json'),source_exposure=packet['exposure'],source_groups=packet['source_groups'],baseline_cases=[dict(case=c['case'],run_id=c['run_id'],target_ids=c['definition']['candidate_targets']) for c in baseline['cases']])
    retain('freeze.json',freeze)
    settings=Settings()
    try:
        with open_runtime_engine(settings,'wce-f37-origins',purpose='evaluate') as engine,engine.connect() as conn:
            origins=tuple(dict(r) for r in conn.execute(text('''SELECT view_.id source_view_id, origin.project_id,origin.origin_group,origin.partition FROM kb.source_view view_ JOIN kb.document document ON document.id=view_.document_id LEFT JOIN eval.reference_origin_source member ON member.project_id=document.project_id AND member.source_uri=document.source_uri LEFT JOIN eval.reference_origin_group origin ON origin.project_id=member.project_id AND origin.origin_group=member.origin_group WHERE view_.id=ANY(:ids) ORDER BY view_.id'''),dict(ids=[s.source_view_id for s in sources])).mappings())
        retain('original-native-origin-partitions.json',origins)
        declared=yaml.safe_load((DOMAINS/'statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates'];base=declared['default']
        config=dict(inputs=inputs.model_dump(mode='json'),structural_input_digest=inputs.identity,target_ids=targets,profile={k:base[k] for k in ('snapshot','checkpoint','revision','artifact_hashes')},annotation_rules=declared['witnessed']['annotation_rules'])
        retain('configuration.json',config)
        bundle,dependencies,profile=compose_pack_inputs((acquire_pack(DOMAINS/'statistics'),))
        prepared=prepare_release(bundle,dependencies,profile);retain('release.json',dict(release_id=prepared.release_id))
        with open_runtime_engine(settings,'wce-f37-release',purpose='admit') as engine,engine.begin() as conn:persist_release(conn,bundle,dependencies,profile,prepared)
        analyzed=None
        if has_authored_sql(prepared):
            with open_runtime_engine(settings,'wce-f37-sql',purpose='read') as engine,engine.connect() as conn:analyzed=analyze_archived_sql(conn,prepared.release_id)
        with open_runtime_engine(settings,'wce-f37-admit',purpose='admit') as engine,engine.begin() as conn:
            if analyzed:admit_archived_sql(conn,prepared.release_id,analyzed=analyzed)
            admit_release(prepared,connection=conn)
        method=DefinitionComponentsMethod();project='wce04-fixed-f37-20261106';realization='wce04-fixed-f37-input:'+prepared.release_id
        registry=MethodRegistry((method,),MethodsFile(configs={method.name:{'default':config}}))
        with open_runtime_engine(settings,'wce-f37-project',purpose='write') as engine,engine.begin() as conn:initialize_source_project(conn,project_id=ProjectId(project),release_id=ReleaseId(prepared.release_id),realization_id=RealizationId(realization),projection_context=prepared)
        with open_runtime_engine(settings,'wce-f37-produce',purpose='write') as engine:
            with engine.connect() as conn:revision=conn.scalar(select(table('data.realization').c.data_revision).where(table('data.realization').c.release_id==prepared.release_id,table('data.realization').c.realization_id==realization))
            result=run_source_methods(engine,project_id=project,prepared=prepared,binding=OperationBinding(prepared.release_id,realization,revision,canonical_bytes({'fixed_sources':freeze['source_packet_sha256'],'fixed_targets':inputs.identity})),registry=registry,graph=Graph(((Stage.EXTRACT,(Step(method.name+'/default'),)),),policy_propose=False),method_settings=MethodSettings(data_dir=HERE/'data',model_cache=Path.home()/'.cache/docling/models'),guideline='Exposed development comparison at exact fixed source targets; preserve unavailable mechanisms and separate attachment from applicability.',kind='full')
            retain('run.json',result.model_dump(mode='json'))
            if result.status!='source_ready':raise ValueError('registered fixed-target producer did not reach source readiness')
            with engine.begin() as conn:cut=seal_cut(conn,result.run_id,'wce04-fixed-f37-final',final=True)
        with open_runtime_engine(settings,'wce-f37-consolidate',purpose='write') as engine:consolidate_cut(engine,cut,'wce04-fixed-f37-result:'+str(result.run_id))
        with open_runtime_engine(settings,'wce-f37-read',purpose='read') as engine,read_snapshot(engine) as conn:
            page=serve_structural_products(conn,StructuralRequest(run_id=result.run_id,kind='definition_components',max_bytes=8_000_000))
            retain('inspection.json',page.model_dump(mode='json'))
            body=conn.scalar(select(table('ops.task_result').c.body).where(table('ops.task_result').c.task_id==page.task_ids[0]));retain('raw-producer-envelope.json',body)
        report=page.reports[0];components=report.definition_components.components
        rows=[]
        for c in judgments['cases']:
            for cell in c['cells']:
                local=[v.model_dump(mode='json') for v in components if v.term.passage_id==cell['target_id']]
                rows.append(dict(case=c['case'],target_id=cell['target_id'],old_observed=cell['observed_category'],old_independent_disposition=cell['independent_disposition'],old_expected=cell['expected_primary_classification'],old_source_reason=cell['source_reason'],current_local_components=local,current_usage_applicability='not_run',comparison='different_statement_types; no precision comparison or claim of corrected whole applicability',preserved_positive='unresolved' if cell['observed_category']=='applicable_definition' and cell['independent_disposition']=='supported' else 'not_applicable'))
        retain('case-ledger.json',rows)
        retain('result.json',dict(outcome='passed',run_id=result.run_id,cut_id=cut,selected_task_ids=page.task_ids,physical_source_views=len(sources),fixed_target_windows=len(targets),component_count=len(components),components_by_basis=dict(Counter(c.basis for c in components)),stages=dict(Counter(s.operation+':'+s.outcome for s in report.definition_components.stages)),baseline_pair_judgments=len(rows),usage_applicability='not_run; component extraction cannot substitute for this question',quality='exposed development-only; local components require independent semantic review'))
        print((HERE/'result.json').read_text())
    except BaseException as error:
        retain('failure.json',dict(outcome='failed',type=type(error).__name__,message=str(error)))
        raise


if __name__=='__main__':main()
