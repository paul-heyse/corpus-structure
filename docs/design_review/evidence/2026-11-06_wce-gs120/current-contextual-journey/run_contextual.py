"""Actual definition-term -> contextual E5 journeys; invocation requires root GO.

Each source has one two-step graph because ordinary source execution owns one
configuration per method per run. All 48 source views and all 35 named components
remain visible; only declared interpretation=definition supplies term/target inputs.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
import traceback

from sqlalchemy import select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.contextual_candidates import ContextualCandidates
from corpus_structure.methods.contextual_embeddings import E5
from corpus_structure.methods.definition_terms import DefinitionTermsMethod
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import RetainedComponentRef
from corpus_structure.serve.contributions import ContributionRequest, export_contribution_selection, serve_contributions
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle, inspect_review_bundle
from corpus_structure.serve.structural_products import StructuralExportRequest, read_structural_export_page
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(BASE / 'current-structural-journey'))
from journey_support import completed_metadata, finish_source_stage, retain, task_custody

PARENT_SHA256 = '763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e'


def capture_named(settings, args, output):
    """Use ordinary exact-cut structural Reader, then authenticate original task refs."""
    with open_runtime_engine(settings, 'gs120-contextual-named', purpose='read') as engine:
        with read_snapshot(engine) as conn:
            run = completed_metadata(conn,args.named_run)
            if run['release_id'] != args.release_id:
                raise ValueError('named run differs from exact root release pin')
            request = StructuralExportRequest(run_id=args.named_run,cut_id=run['cut_id'],kind='definition_components',max_bytes=128_000_000)
            page = read_structural_export_page(conn,request)
            if len(page.reports) != 1 or page.next_after_task_id is not None:
                raise ValueError('require exactly one full named component report')
            report = page.reports[0]
            if report.product_id != args.named_product:
                raise ValueError('named report differs from root product pin')
            custody = task_custody(conn,run)
            selected = page.task_ids[0]
            origin = custody[selected]
            raw = conn.execute(text('SELECT r.body,m.name,m.version FROM ops.task_result r JOIN ops.task t ON t.id=r.task_id JOIN ops.method_config c ON c.id=t.method_config_id JOIN ops.method m ON m.id=c.method_id WHERE r.task_id=:task'),dict(task=origin['origin_task_id'])).mappings().one()
            refs = [RetainedComponentRef(product_id=report.product_id,component_id=c.component_id,operation_id=raw['name'],operation_version=raw['version'],project_id=run['project_id'],run_id=run['run_id'],cut_id=run['cut_id'],release_id=run['release_id'],result_revision=run['result_revision'],dependencies=report.inputs.dependencies,**origin) for c in report.definition_components.components]
            # Native custody checks are read-only; no synthesized or caller supplied mentions.
            for ref in refs:
                resolved = conn.execute(text('SELECT ops.resolve_retained_component(CAST(:reference AS jsonb))'),dict(reference=canonical_bytes(ref.model_dump(mode='json')).decode())).scalar_one()
                if resolved['component']['component_id'] != ref.component_id:
                    raise ValueError('native component resolution changed selector')
    retain(output/'named-file-page.json',page.model_dump(mode='json'))
    retain(output/'named-custody.json',dict(run=run,selected_task_id=selected,origin=origin,method=raw['name'],version=raw['version'],raw_body_sha256=sha256(canonical_bytes(raw['body'])).hexdigest()))
    retain(output/'all-component-references.json',[r.model_dump(mode='json') for r in refs])
    return run,report,dict(zip((c.component_id for c in report.definition_components.components),refs,strict=True))


def prepare_inventory(report,refs,output):
    packet_path = BASE/'source-recovery/attempt001/source-packets/source-packet.json'
    packet = json.loads(packet_path.read_bytes())
    coverage = json.loads((packet_path.parent.parent/'coverage.json').read_bytes())
    if packet['source_manifest']['parent_sha256'] != PARENT_SHA256 or packet['predictions_included']:
        raise ValueError('not the fixed neutral GS120 packet')
    if coverage['outcome'] != 'passed' or coverage['native_item_pages'] != list(range(191,311)) or coverage['projected_text_pages'] != list(range(191,311)):
        raise ValueError('fixed120-page source coverage differs')
    if len(report.inputs.sources) != 48 or len(report.definition_components.components) != 35:
        raise ValueError('expected all48 sources and all35 named components')
    if report.inputs.model_dump(mode='json')['sources'] != packet['sources'] or report.inputs.model_dump(mode='json')['passages'] != packet['passages']:
        raise ValueError('final named sources/passages differ from fixed neutral packet')
    components = report.definition_components.components
    eligible = tuple(c for c in components if c.interpretation == 'definition')
    targets = [dict(reference=refs[c.component_id].model_dump(mode='json'),label=c.term.text,description=c.content.text,scope=c.scope,effective_version=c.effective_version) for c in eligible]
    # No public/protected gold labels influence this filter or descriptor population.
    by_passage = {p.passage_id:p for p in report.inputs.passages}
    by_source = {s.identity:s for s in report.inputs.sources}
    views = []
    for source in report.inputs.sources:
        own = tuple(c for c in components if by_passage[c.term.passage_id].source_ref == source.identity)
        selected = tuple(c for c in own if c.interpretation == 'definition')
        views.append(dict(source=source.model_dump(mode='json'),all_component_ids=[c.component_id for c in own],eligible_component_ids=[c.component_id for c in selected],unselected=[dict(component_id=c.component_id,interpretation=c.interpretation,reason='Declared interpretation is not definition; no defined-by term/target projection authorized by this arm.') for c in own if c.interpretation != 'definition'],phase_outcome='prepared' if selected else 'not_run',reason=None if selected else 'No eligible declared definition component in this source view.'))
    inventory = dict(protocol='gs120-current-contextual-inventory-1',named_product_id=report.product_id,physical_pages=list(range(191,311)),parent_sha256=PARENT_SHA256,source_packet_sha256=sha256(packet_path.read_bytes()).hexdigest(),selection_rule="component.interpretation == 'definition'",all_components=[c.model_dump(mode='json') for c in components],selected_component_ids=[c.component_id for c in eligible],unselected_component_ids=[c.component_id for c in components if c.interpretation != 'definition'],target_components=targets,source_views=views,standing='retained_private',semantic_quality='unassessed',scientific_support='unmodeled',similarity_is_identity=False,profile=asdict(E5),protected_gold_filter_used=False)
    retain(output/'inventory.json',inventory)
    return inventory


def run_view(settings,prepared,report,targets,refs,view,output,attempt):
    source_id=view['source']['source_view_id']
    source = next(s for s in report.inputs.sources if s.source_view_id==source_id)
    root=output/('source-'+str(source_id));root.mkdir(exist_ok=True)
    if not view['eligible_component_ids']:
        retain(root/'result.json',dict(outcome='not_run',source_view_id=source_id,reason=view['reason'],source_selection_preserved=True))
        return dict(source_view_id=source_id,outcome='not_run',reason=view['reason'])
    locate=DefinitionTermsMethod();retrieve=ContextualCandidates()
    configs={locate.name:{'current':dict(component_refs=[refs[c].model_dump(mode='json') for c in view['eligible_component_ids']],source_product_digest=source.native_content_digest,source_projection_digest=source.projection_digest)},retrieve.name:{'current':dict(profile='e5',source_dependency_method=locate.name,semantic_types=['definition.term'],target_components=targets,relationship_constraints=[dict(constraint_id='source-declared-defined-term',relation_kinds=['defined-by'],occurrence_role='defined_term',target_role='retained_definition_component',multiplicity='one',exhaustive=False)],source_product_digest=source.native_content_digest,source_projection_digest=source.projection_digest,scope=report.inputs.scope,unique_target_budget=min(100,len(targets)),channel_budget=max(30,len(targets)))}}
    registry=MethodRegistry((locate,retrieve),MethodsFile(configs=configs))
    for method in (locate,retrieve):
        registry.resolve(method.name,'current')
    retain(root/'configuration.json',dict(configs=configs,graph=[locate.name+'/current',retrieve.name+'/current'],all48_sources_selected=True))
    if (root/'completed.json').exists():
        run=json.loads((root/'completed.json').read_bytes())
    elif (root/'source-ready.json').exists():
        ready=json.loads((root/'source-ready.json').read_bytes());run=finish_source_stage(settings,ready['run_id'],root)
    else:
        realization='gs120-current-contextual:'+attempt+':source-'+str(source_id)+':'+prepared.release_id
        with open_runtime_engine(settings,'gs120-contextual-source-'+str(source_id),purpose='write') as engine:
            with engine.begin() as conn:
                initialize_source_project(conn,project_id=ProjectId(source.project_id),release_id=ReleaseId(prepared.release_id),realization_id=RealizationId(realization),projection_context=prepared)
            with read_snapshot(engine) as conn:
                t=table('data.realization');revision=conn.scalar(select(t.c.data_revision).where(t.c.realization_id==realization))
            result=run_source_methods(engine,project_id=source.project_id,prepared=prepared,binding=OperationBinding(prepared.release_id,realization,revision,canonical_bytes(dict(parent_sha256=PARENT_SHA256,named_product=report.product_id,source_view_id=source_id,attempt=attempt))),registry=registry,graph=Graph(((Stage.SCOPE,(Step(locate.name+'/current'),Step(retrieve.name+'/current',upstream=(locate.name,)))),),policy_propose=False),method_settings=MethodSettings(data_dir=root/'data',model_cache=Path.home()/'.cache/docling/models'),guideline=(DOMAINS/'statistics/m1-guideline.md').read_text(),policy_source=None,kind='full',selected_sources=report.inputs.sources)
            retain(root/'source-ready.json',result.model_dump(mode='json'))
            if result.status!='source_ready':raise ValueError('two-step graph did not reach source_ready')
        run=finish_source_stage(settings,result.run_id,root)
    requests=[]
    with open_runtime_engine(settings,'gs120-contextual-reader',purpose='read') as engine:
        with read_snapshot(engine) as conn:
            for method in (locate,retrieve):
                request=ContributionRequest(run_id=run['run_id'],source_view_id=source_id,method=method.name,include_interpretation=True,limit=1000,page_bytes=16_000_000,max_bytes=128_000_000)
                requests.append(request);pages=[];cursor_request=request
                while True:
                    page=serve_contributions(conn,cursor_request);pages.append(page.model_dump(mode='json'))
                    if page.next_cursor is None:break
                    cursor_request=request.model_copy(update=dict(cursor=page.next_cursor))
                key=method.name.replace('.','-');retain(root/(key+'-pages.json'),pages)
                destination=root/(key+'-export')
                if not destination.exists():manifest=export_contribution_selection(conn,request,destination)
                else:
                    manifest=json.loads((destination/'manifest.json').read_bytes())
                    if manifest['run_id']!=run['run_id'] or manifest['cut_id']!=run['cut_id'] or manifest['selection']!=request.selection() or sha256((destination/manifest['file']).read_bytes()).hexdigest()!=manifest['sha256']:raise ValueError('existing ordinary export differs')
                retain(root/(key+'-export.json'),manifest)
    selection=ReviewSelection(selections=tuple(requests),structural_selections=(StructuralExportRequest(run_id=refs[view['eligible_component_ids'][0]].run_id,kind='definition_components',max_bytes=128_000_000),),max_bytes=256_000_000)
    bundle=root/'review'
    if not bundle.exists():export_review_bundle(selection,bundle,settings)
    manifest=json.loads((bundle/'manifest.json').read_bytes())
    if manifest['selection']!=selection.model_dump(mode='json'):raise ValueError('portable selection differs')
    detached=inspect_review_bundle(bundle);retain(root/'portable-closure.json',detached)
    summary=summarize_raw(bundle,source_id)
    summary.update(run=run,source_view_id=source_id,ordinary_reader_export='passed',portable_closure='passed',standing='retained_private',semantic_quality='unassessed',scientific_support='unmodeled',similarity_is_identity=False)
    retain(root/'result.json',summary)
    return summary


def summarize_raw(bundle,source_id):
    phases=[];retrievals=[];decisions=[];implementations=[]
    for line in (bundle/'reports.jsonl').read_bytes().splitlines():
        raw=json.loads(json.loads(line)['payload_json']);body=raw.get('body') or {}
        if body.get('method')!=ContextualCandidates.name or raw.get('origin_unit_id')!=source_id:continue
        for operation in body.get('contribution_operations',()):
            phases.append({k:v for k,v in operation.items() if k!='contextual_enrichment'})
            enriched=operation.get('contextual_enrichment')
            if enriched:
                retrievals.extend(enriched.get('candidate_lists',()))
                decisions.extend(enriched.get('relationship_decisions',()))
        if body.get('parse_detail') is not None:implementations.append(body['parse_detail'])
    failed=[p for p in phases if p.get('outcome') in ('failed','not_run')]
    return dict(outcome='failed' if failed or not phases else 'passed',phase_operations=phases,candidate_lists=retrievals,relationship_decisions=decisions,encoder_parse_detail=implementations,phase_outcomes=dict(Counter(p.get('outcome') for p in phases)),relationship_outcomes=dict(Counter(d.get('outcome') for d in decisions)),meaning='Candidate retrieval/selection diagnostic only; similarity assigns neither canonical identity nor public truth.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--named-run',type=int,required=True);parser.add_argument('--named-product',required=True);parser.add_argument('--release-id',required=True);parser.add_argument('--attempt',required=True)
    parser.add_argument('--root-go',action='store_true',help='Coordinator confirms exact deployed baseline and authorizes actual DB/provider work.')
    args=parser.parse_args()
    if not args.root_go:parser.error('No DB/provider call permitted before explicit root GO; prepared script is read-only until then.')
    output=HERE/args.attempt;output.mkdir(exist_ok=True)
    try:
        settings=Settings();run,report,refs=capture_named(settings,args,output)
        inventory=prepare_inventory(report,refs,output)
        with open_runtime_engine(settings,'gs120-contextual-release',purpose='read') as engine:
            with read_snapshot(engine) as conn:prepared=load_release(conn,args.release_id)
        retain(output/'release.json',dict(release_id=prepared.release_id,acquisition='exact root-pinned existing release; no admission/generation'))
        results=[]
        for view in inventory['source_views']:
            try:result=run_view(settings,prepared,report,inventory['target_components'],refs,view,output,args.attempt)
            except Exception as error:
                root=output/('source-'+str(view['source']['source_view_id']));root.mkdir(exist_ok=True)
                result=dict(source_view_id=view['source']['source_view_id'],outcome='failed',type=type(error).__name__,message=str(error));retain(root/'failure.json',result)
                (root/'failure-traceback.txt').write_text(traceback.format_exc())
            results.append(result);print(json.dumps(dict(source_view_id=result['source_view_id'],outcome=result['outcome'])),flush=True)
        retain(output/'result.json',dict(outcome='failed' if any(r['outcome']=='failed' for r in results) else 'passed',named_run=run,named_product_id=report.product_id,all_components=35,sources=48,pages=120,selection_rule=inventory['selection_rule'],selected_components=len(inventory['selected_component_ids']),unselected_components=len(inventory['unselected_component_ids']),source_outcomes=results,meaning='All selected definition inputs attempted. Explanations and views without eligible terms retained explicitly. Provider/contribution/portable outcomes are operational; semantic quality unassessed.'))
    except BaseException as error:
        retain(output/'failure.json',dict(outcome='failed',type=type(error).__name__,message=str(error)));raise


if __name__=='__main__':main()
