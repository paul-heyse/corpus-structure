"""Prepare B's bounded exact literals from independently selected source text; no DB access."""
import argparse
import hashlib
import json
from pathlib import Path

from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference, StructuralEvaluationFrame, StructuralReferenceCase,
    StructuralSourceGroup, StructuralSourceOpportunity, score_structural_reference,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.semantic.structural_admission import structural_statement
from author_b import B_CASES

HERE=Path(__file__).resolve().parent
GS=HERE.parents[1]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def source_selected(packet_name,pointer,literal,packets,inputs,occurrence=None):
    options=[]
    for path,p in packets.items():
        for j,v in enumerate(p['views']):
            if v['native_view']['source_uri']!=packet_name: continue
            for piece in v['native_context']['pieces']:
                if piece.get('item_ref')!=pointer or piece.get('kind')!='native_text':continue
                if piece.get('source_field')!='text':continue
                host=v['passage']['text'][piece['start']:piece['end']]
                positions=[];pos=host.find(literal)
                while pos>=0: positions.append(pos);pos=host.find(literal,pos+1)
                if occurrence is None and len(positions)!=1:continue
                if occurrence is not None and not 0<=occurrence<len(positions):continue
                src=next((s for s in inputs.sources if s.source_view_id==v['source']['source_view_id']),None)
                if src is None:continue
                if src.model_dump(mode='json')!=v['source']:raise ValueError('source packet/current input pin mismatch')
                offset=positions[0 if occurrence is None else occurrence];start=piece['start']+offset;end=start+len(literal)
                node=next(it for it in v['native_context']['items'] if it.get('self_ref')==pointer)
                options.append((v,dict(passage_id=v['passage']['passage_id'],start=start,end=end,text=literal),
                    dict(packet=str(path),packet_sha256=sha(path),view_index=j,source_pin=v['source'],
                         native_pointer=pointer,source_field='text',native_start=offset,native_end=offset+len(literal),
                         quote=literal,piece=piece,original_item_text=node.get('orig'),converted_item_text=node['text'],
                         provenance=node.get('prov',[]),anchor_state='independently located native-anchor specification; production anchor ID awaits authentic native unit key')))
    if len(options)!=1:raise ValueError(f'independent quote has {len(options)} exact source matches: {packet_name} {pointer} {literal!r}')
    return options[0]

def citation(inputs,span):
    p=next(p for p in inputs.passages if p.passage_id==span['passage_id'])
    s=next(s for s in inputs.sources if s.identity==p.source_ref)
    src={k:v for k,v in s.model_dump(mode='json',exclude_none=True).items() if k not in {'run_id','cut_id','release_id','result_revision','source_view_id','native_task_id'}}
    # Frame metadata binds independent source wording; no actual component selects expected semantics.
    return dict(source=src,**p.model_dump(mode='json',exclude_none=True,exclude={'passage_id','source_ref','start','end','text'}),**span_without_id(span))

def span_without_id(span):return {k:v for k,v in span.items() if k!='passage_id'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inspection',type=Path,default=GS/'current-extraction/named001/structural-inspection.json');parser.add_argument('--out',type=Path,default=HERE/'prepared-b-run152');args=parser.parse_args()
    raw=json.loads(args.inspection.read_text());product=StructuralProductReport.model_validate(raw['reports'][0]);inputs=product.inputs
    if inputs.exclusions:raise ValueError('nonempty exclusion population needs separately authored literal rendering')
    packets={p:json.loads(p.read_text()) for p in (GS/'source-recovery/attempt001/source-packets').glob('grinstead-snell-physical*.json')}
    ids={c.component_id for c in product.definition_components.components};all_passages=tuple(p.passage_id for p in inputs.passages)
    cases=[];opportunities=[];authoring=[]
    prior_b=json.loads((GS/'authors/current-named-review/b/assessment.json').read_text())
    prior_facets={e['component_id']:e['facets'] for e in prior_b['entries']}
    for spec in B_CASES:
        if spec['component_id'] not in ids:raise ValueError('assessed output ID missing; root must authenticate a final output correspondence, not infer one')
        tv,term,ta=source_selected(spec['source_uri'],spec['term_pointer'],spec['term'],packets,inputs,spec.get('term_occurrence'))
        cv,content,ca=source_selected(spec['source_uri'],spec['content_pointer'],spec['content'],packets,inputs)
        context=[]
        # Context quotes are independently authored and may occupy a different item in the same source view.
        for q in spec['context']:
            pos=tv['passage']['text'].find(q)
            if pos<0:raise ValueError('independent context quote not present')
            context.append(dict(passage_id=tv['passage']['passage_id'],start=pos,end=pos+len(q),text=q))
        expected={'version':'structural-public-statement-3','kind':'definition_components','scope':inputs.scope,
                  'coverage_limits':sorted(inputs.coverage_limits),'exclusions':[],
                  'definition_component':{'term':citation(inputs,term),'content':citation(inputs,content),
                                          'interpretation':spec['interpretation'],'scope':inputs.scope}}
        cases.append(StructuralReferenceCase(case_id=spec['case_id'],component_id=spec['component_id'],facet='public_statement',path=('public_statement',),expected=expected,source_passages=all_passages,judgment=spec['judgment'],explanation=spec['reason']))
        opportunities.append(StructuralSourceOpportunity(opportunity_id=spec['case_id'],passage_id=term['passage_id'],facet='public_statement',source_state='stated'))
        authoring.append(dict(case_id=spec['case_id'],author='B',expectation_origin='B independently authored literal source selections in author_b.py; C alternatives were not used',term_anchor=ta,content_anchor=ca,context_quotes=context,typed_case=cases[-1].model_dump(mode='json',exclude_none=True),B_six_facets=prior_facets[spec['component_id']],limits='Exact narrow attachment only; all frame passage IDs are citation closure required by native public-statement case ingress, not a claim to full semantic correctness of all48 views.'))
    cases.append(StructuralReferenceCase(case_id='B-WHOLE-REPORT-COMPLETENESS-UNASSESSED',facet='completeness',path=('definition_components','components'),expected=None,source_passages=all_passages,judgment='unassessed',explanation='No independently authored complete whole-report expectation exists. These selective cases supply no whole-report correctness or blanket public eligibility; expected null is deliberately not a positive alternative.'))
    opportunities.append(StructuralSourceOpportunity(opportunity_id=cases[-1].case_id,passage_id=all_passages[0],facet='completeness',source_state='uninspected'))
    frame=StructuralEvaluationFrame(inputs=inputs,operation='definition_components',direction='output_first',rubric_version='independent-definition-component-1',rubric_text='Independently source-authored exact narrow source-attributed attachment. Partial local naming/formula support is separate from full scope, recognition fidelity, scientific truth, and whole-report completeness. No held-out claim.',product_ids=(product.product_id,),partition='development',source_groups=tuple(StructuralSourceGroup(source_ref=s.identity,origin_group='grinstead-snell') for s in inputs.sources),opportunities=tuple(opportunities),inspected_scope='B bounded normal-density/marginal-totals/probability-subject/historical-contrast literal cases; whole report completeness unassessed',exposure_history=('B reviewed baseline9, replay41, current35 outputs and corresponding sources; development evidence','B now integrating frozen A/B/C evidence; these B meanings authored from B source reading, not C expected values'))
    reference=StructuralAuthoredReference(frame_digest=frame.identity,cases=tuple(cases))
    comparison=score_structural_reference(frame,reference,product.model_dump(mode='json',exclude_none=True))
    try:structural_statement(product)
    except ValueError as e:refusal={'outcome':'refused','reason':str(e),'scope':'No whole-report definition-component statement selector; literal owner refusal, not a stored public_statement gold case.'}
    else:raise ValueError('whole-report structural owner unexpectedly accepted missing component selector')
    args.out.mkdir(parents=True,exist_ok=True)
    for name,value in [('frame.json',frame.model_dump(mode='json',exclude_none=True)),('B.authored.json',reference.model_dump(mode='json')),('B.authoring-provenance.json',authoring),('local-comparison.json',comparison),('whole-report-refusal.json',refusal)]:
        (args.out/name).write_bytes(canonical_bytes(value)+b'\n')
    receipt={'outcome':'passed','database_writes':'not_run','protected_import':'not_run_waiting_root_GO','source_inspection':str(args.inspection),'source_inspection_sha256':sha(args.inspection),'product_id':product.product_id,'frame_digest':frame.identity,'B_authored_sha256':sha(args.out/'B.authored.json'),'cases':[{'case_id':c['case_id'],'judgment':c['judgment'],'outcome':c['outcome']} for c in comparison['cases']],'whole_report_refusal':refusal,'limits':'Local typed preparation only; no native protected custody and no A/B/C consensus claim.'}
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
