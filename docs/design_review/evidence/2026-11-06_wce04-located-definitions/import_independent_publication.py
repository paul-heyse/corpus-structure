"""Faithfully adapt independent authored files; the importer authors no judgments.

A/B/C retain their own raw bytes, actors, source coordinates and differing facet
populations. Only the byte-identical component is transported from the authors'
original output freeze to the final producer; whole-report judgments are not moved.
"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference, StructuralEvaluationFrame, StructuralReferenceCase,
    StructuralSourceGroup, StructuralSourceOpportunity, create_structural_reference_set,
    record_structural_reference_pass, score_structural_reference,
)
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, create_run, create_task, start_run
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_run
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle, verify_review_bundle
from corpus_structure.serve.structural_products import StructuralRequest, serve_structural_products
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
RAW=Path('/home/paul/corpus-structure/docs/design_review/evidence/2026-11-06_wce-definition-linking')


def retain(path,value):
    path.write_bytes(canonical_bytes(value)+b'\n')


def raw_file(name):
    data=(RAW/name).read_bytes()
    return json.loads(data),sha256(data).hexdigest()


def facets(payload):
    c=payload['components'][0]
    return c.get('facet_judgments',c.get('facets'))


def own_extent(facets_,names,source_text):
    selected=[f for f in facets_ if f['facet'] in names]
    if len(selected)!=1 or selected[0]['judgment']!='supported' or len(selected[0]['spans'])!=1:
        raise ValueError('independent literal-location evidence is not unique and supported')
    span=selected[0]['spans'][0]
    if source_text[span['start']:span['end']] != span['text']:
        raise ValueError('independent expected quote differs from frozen source')
    return dict(start=span['start'],end=span['end'],text=span['text'])


def expected_statement(payload,report):
    fs=facets(payload)
    term=own_extent(fs,{'term_location','term_literal_location'},report.inputs.passages[0].text)
    content=own_extent(fs,{'defining_content_location','content_literal_location','defining_content_literal_location'},report.inputs.passages[0].text)
    required=( {'term_role','term_semantic_role'}, {'defining_content_role','content_semantic_role','defining_content_semantic_role'}, {'term_content_attachment','term_to_formula_attachment'}, {'definition_interpretation'}, {'local_scope','scope_source_context','local_scope_and_family_context'})
    for group in required:
        if not any(f['facet'] in group and f['judgment']=='supported' for f in fs):
            raise ValueError('author did not independently support every narrow attachment premise')
    passage=report.inputs.passages[0]
    source=report.inputs.sources[0]
    # Frozen native source/citation metadata is context, not an authored label.
    physical={k:v for k,v in source.model_dump(mode='json').items() if k not in {'run_id','cut_id','release_id','result_revision','source_view_id','native_task_id'}}
    citation=lambda span:dict(source=physical,**span,scope=passage.scope)
    return dict(version='structural-public-statement-2',kind='definition_components',scope=report.inputs.scope,coverage_limits=list(report.inputs.coverage_limits),exclusions=[],definition_component=dict(term=citation(term),content=citation(content),interpretation='definition',scope=passage.scope))


def author_reference(frame,payload,digest,source_payload,source_digest,report):
    passage=report.inputs.passages[0]
    expected=expected_statement(payload,report)
    term={k:v for k,v in expected['definition_component']['term'].items() if k!='source' and k!='scope'}
    term['passage_id']=passage.passage_id
    content={k:v for k,v in expected['definition_component']['content'].items() if k!='source' and k!='scope'}
    content['passage_id']=passage.passage_id
    cases=[]
    for index,f in enumerate(facets(payload)):
        name=f['facet'];judgment=f['judgment'];path=('definition_components','components',0);value=f
        if judgment=='supported':
            if name in {'term_location','term_literal_location','term_role','term_semantic_role','grammatical_article_and_core_boundary','term_boundary','article_core_and_referring_phrase_boundary'}:
                path=(*path,'term');value=term
            elif name in {'defining_content_location','content_literal_location','defining_content_literal_location','defining_content_role','content_semantic_role','defining_content_semantic_role','content_boundary','defining_content_boundary'}:
                path=(*path,'content');value=content
            elif name in {'term_content_attachment','term_to_formula_attachment','definition_interpretation'}:
                path=(*path,'interpretation');value='definition'
            elif name in {'local_scope','scope_source_context','local_scope_and_family_context'}:
                path=(*path,'scope');value=passage.scope
            else:
                # Supported source parameters do not assert complete emitted capture.
                judgment='unassessed'
        facet='applicability' if 'applicability' in name else 'completeness' if any(t in name for t in ('complete','coverage','condition','parameter','geometry','recognition','truth','version')) else 'location' if 'location' in name or 'boundary' in name else 'attachment' if 'attachment' in name else 'scope' if 'scope' in name else 'role'
        cases.append(StructuralReferenceCase(case_id='output:'+str(index)+':'+name,component_id=report.definition_components.components[0].component_id,facet=facet,path=path,expected=value,source_passages=(passage.passage_id,),judgment=judgment,explanation=f['reason']+' [Independent raw actor '+payload['actor']+'; file SHA256 '+digest+'; original facet '+name+'. Source-only parameter support is distinct from emitted capture.]'))
    cases.append(StructuralReferenceCase(case_id='exact-located-attachment',component_id=report.definition_components.components[0].component_id,facet='public_statement',path=('public_statement',),expected=expected,source_passages=(passage.passage_id,),judgment='supported',explanation='Exact narrow attachment assembled only from this author\'s separately supported literal term/content, roles, attachment, definition interpretation and local source scope. No geometry, scientific truth, full condition capture or usage applicability authority. Raw SHA256 '+digest))
    cases.append(StructuralReferenceCase(case_id='raw-author-provenance',facet='source_support',path=('raw_author_provenance',),expected=dict(output_actor=payload['actor'],output_sha256=digest,source_actor=source_payload['actor'],source_sha256=source_digest,raw_output=payload),source_passages=(passage.passage_id,),judgment='unassessed',explanation='Protected original authored evidence and exact input provenance; no output grade added.'))
    return StructuralAuthoredReference(frame_digest=frame.identity,cases=tuple(cases))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
    output=HERE/('publication'+args.attempt);output.mkdir(exist_ok=False)
    settings=Settings(); inspection=json.loads((HERE/'native005/inspection.json').read_bytes());report=StructuralProductReport.model_validate(inspection['reports'][0]);producer_run=inspection['run_id'];producer_task=inspection['task_ids'][0]
    payloads={};sources={}
    for kind in 'ABC':
        payloads[kind]=raw_file('output-author-'+kind.lower()+'.json')
        sources[kind]=raw_file('author-'+kind.lower()+'.json')
    old=StructuralProductReport.model_validate(json.loads((HERE/'native003/inspection.json').read_bytes())['reports'][0])
    assert old.definition_components.components==report.definition_components.components
    original_source=json.loads((RAW/'source-author-input.json').read_bytes())
    assert original_source['passages'][0]['text']==report.inputs.passages[0].text
    try:
        with open_runtime_engine(settings,'wce-independent-reference-context',purpose='evaluate') as engine,engine.connect() as conn:
            origin=conn.execute(text('''SELECT origin.origin_group,origin.partition FROM kb.source_view view_ JOIN kb.document document ON document.id=view_.document_id JOIN eval.reference_origin_source member ON member.project_id=document.project_id AND member.source_uri=document.source_uri JOIN eval.reference_origin_group origin ON origin.project_id=member.project_id AND origin.origin_group=member.origin_group WHERE view_.id=53''')).mappings().one()
            assert origin['partition']=='feature_fit'
        source_groups=(StructuralSourceGroup(source_ref=report.inputs.sources[0].identity,origin_group=origin['origin_group']),)
        source_frame=StructuralEvaluationFrame(inputs=report.inputs,operation='definition_components',direction='source_first',rubric_version='independent-source-reference-preservation-1',rubric_text='Preserve independently authored source propositions and their original judgments. Emitted capture is unassessed without output alignment.',partition='feature_fit',source_groups=source_groups,opportunities=tuple(StructuralSourceOpportunity(opportunity_id=c['case_id'],passage_id=report.inputs.passages[0].passage_id,facet=c['facet'],source_state='uninspected' if c['judgment']=='unassessed' else 'unresolved' if c['judgment']=='ambiguous' else 'stated') for c in sources['C'][0]['cases']),inspected_scope='Original5684-character normal-source passage; source-family exposure preserved.',exposure_history=('Original source family already exposed before this feature-fit refinement; no held-out claim.',))
        frame=StructuralEvaluationFrame(inputs=report.inputs,operation='definition_components',direction='output_first',product_ids=(report.product_id,),rubric_version='independent-definition-component-1',rubric_text='Located term/content roles and exact local attachment only; no uniqueness, geometry, full condition capture, usage applicability or scientific truth.',partition='feature_fit',source_groups=source_groups,opportunities=tuple(StructuralSourceOpportunity(opportunity_id='facet:'+f['facet'],passage_id=report.inputs.passages[0].passage_id,facet=f['facet'],source_state='uninspected' if f['judgment']=='unassessed' else 'stated') for f in facets(payloads['C'][0])),inspected_scope='One byte-identical independently inspected component, frozen from original118 output to final120; whole-report assessments not transferred.',exposure_history=('Already exposed original feature-fit source; original author freezes and parent hashes retained.',))
        retain(output/'frame.json',frame.model_dump(mode='json'));retain(output/'source-frame.json',source_frame.model_dump(mode='json'))
        references={kind:author_reference(frame,*payloads[kind],*sources[kind],report) for kind in 'ABC'}
        receipts={}
        with open_runtime_engine(settings,'wce-independent-reference-import',purpose='evaluate') as engine,engine.begin() as conn:
            source_set=create_structural_reference_set(conn,project_id='wce04-normal-definitions-20261106',release_id=inspection['release_id'],frame=source_frame)
            source_passes=[]
            for kind in 'ABC':
                raw,digest=sources[kind]
                cases=tuple(StructuralReferenceCase(case_id=c['case_id'],facet='source_support',path=('source_reference_cases',c['case_id']),expected=dict(original_source_case=c,raw_actor=raw['actor'],raw_file_sha256=digest),source_passages=(report.inputs.passages[0].passage_id,),judgment='unassessed',explanation='Original source semantic judgment retained verbatim; output capture not independently aligned by this source-only pass.') for c in raw['cases'])
                authored=StructuralAuthoredReference(frame_digest=source_frame.identity,cases=cases)
                source_passes.append(record_structural_reference_pass(conn,set_id=source_set,pass_kind=kind,actor=raw['actor'],authored=canonical_bytes(authored.model_dump(mode='json',exclude_none=True)),parents=tuple(source_passes) if kind=='C' else ()))
            set_id=create_structural_reference_set(conn,project_id='wce04-normal-definitions-20261106',release_id=inspection['release_id'],frame=frame)
            passes=[]
            for kind in 'ABC':
                passes.append(record_structural_reference_pass(conn,set_id=set_id,pass_kind=kind,actor=payloads[kind][0]['actor'],authored=canonical_bytes(references[kind].model_dump(mode='json',exclude_none=True)),parents=tuple(passes) if kind=='C' else ()))
            digest=conn.scalar(select(table('eval.structural_reference_pass').c.content_digest).where(table('eval.structural_reference_pass').c.id==passes[2]))
            receipts=dict(source_set_id=source_set,source_pass_ids=source_passes,source_case_counts={k:len(v[0]['cases']) for k,v in sources.items()},output_set_id=set_id,output_pass_ids=passes,output_case_counts={k:len(facets(v[0])) for k,v in payloads.items()},c_content_digest=digest)
        retain(output/'protected-reference-receipt.json',receipts)
        comparison=score_structural_reference(frame,references['C'],report.model_dump(mode='json'))
        retain(output/'comparison.json',comparison)
        assert all(c['outcome']=='match' for c in comparison['cases'] if c['judgment']=='supported')
        admission=dict(product_id=report.product_id,component_id=report.definition_components.components[0].component_id,set_id=set_id,c_pass_id=passes[2],c_content_digest=digest,frame_digest=frame.identity,policy_id='independent-definition-component-1')
        with open_runtime_engine(settings,'wce-independent-component-publication',purpose='write') as engine:
            with engine.begin() as conn:
                job=dict(conn.execute(select(table('ops.run')).where(table('ops.run').c.id==producer_run)).mappings().one());task=dict(conn.execute(select(table('ops.task')).where(table('ops.task').c.id==producer_task)).mappings().one())
                prepared=open_release(conn,job['release_id']);runtime=runtime_binding_for_run(conn,producer_run,prepared)
                dependencies=json.loads(bytes(job['dependencies']));dependencies['structural_admission']=[admission]
                run=create_run(conn,project_id=job['project_id'],binding=OperationBinding(job['release_id'],job['input_realization_id'],job['input_revision'],canonical_bytes(dependencies)),kind='full',options=job['options'],code_commit=job['code_commit'],guideline=job['guideline'],phase=job['phase'],prepared=prepared,runtime_binding=runtime)
                start_run(conn,run,prepared=prepared)
                selected=create_task(conn,run_id=run,config_id=task['method_config_id'],stage=task['stage'],unit_type=task['unit_type'],input_hash=task['input_hash'],unit_id=task['unit_id'],unit_key=task['unit_key'],packet_hash=task['packet_hash'])
                reused=conn.execute(select(table('ops.task').c.reused_task_id).where(table('ops.task').c.id==selected)).scalar_one()
                assert reused==producer_task,'publication must reuse frozen producer; no post-label inference permitted'
            finalize_bound_run(engine,run,'wce04-independent-component-publication:'+str(run))
            with read_snapshot(engine) as conn:
                page=serve_structural_products(conn,StructuralRequest(run_id=run,include_publication=True,include_support=True))
                assert len(page.public_assertions)==1 and page.reports[0].standing=='private_proposal'
                retain(output/'ordinary-inspection.json',page.model_dump(mode='json'))
        exported=export_review_bundle(ReviewSelection(structural_selections=(StructuralRequest(run_id=run,include_publication=True,include_support=True),)),output/'review-bundle',settings)
        retain(output/'export-receipt.json',exported);verified=verify_review_bundle(output/'review-bundle');retain(output/'export-verification.json',verified)
        retain(output/'result.json',dict(outcome='passed',publication_run=run,selected_task=selected,origin_task=producer_task,producer_parameters_changed=False,producer_reexecuted=False,public_assertions=1,scope='Exact independently supported located attachment only; usage applicability and scientific truth unassessed.',**receipts))
        print((output/'result.json').read_text())
    except BaseException as error:
        retain(output/'failure.json',dict(outcome='failed',type=type(error).__name__,message=str(error)))
        raise


if __name__=='__main__':main()
