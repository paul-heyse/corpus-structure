"""Independent C model-addition judgments and actual raw-provider inventory."""
from collections import Counter
from functools import cache
import hashlib
import json
from pathlib import Path

from corpus_structure.semantic.observations import source_python

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREFIX='assessment/run161-final-model001/'
PINS=set()


@cache
def read(path):
    PINS.add(path)
    return json.loads((ROOT/path).read_text())


def pin(path):
    PINS.add(path)
    return {'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}


def write(name,obj):
    (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


def packets(prefix):
    views={}
    for p in sorted((ROOT/prefix).glob('grinstead*.json')):
        rel=str(p.relative_to(ROOT));packet=read(rel)
        for v in packet['views']:views[v['passage']['passage_id']]=(packet,v,rel)
    return views


def endpoint(ep,views):
    packet,v,path=views[ep['passage_id']];n=v['native_view'];s,e=ep['start'],ep['end']
    assert v['passage']['text'][s:e]==ep['text']
    segs=[]
    for piece in v['native_context']['pieces']:
        if piece.get('item_ref') and piece['start']<e and piece['end']>s:
            lo,hi=max(s,piece['start'])-piece['start'],min(e,piece['end'])-piece['start']
            item=next(x for x in v['native_context']['items'] if x['self_ref']==piece['item_ref'])
            leaf=item['data']['table_cells'][piece['cell_index']]['text'] if piece['source_field']=='cell_text' else item[piece['source_field']]
            segs.append({'native_pointer':piece['item_ref'],'field':piece['source_field'],'cell_index':piece.get('cell_index'),
                         'native_start':lo,'native_end':hi,'text':leaf[lo:hi]})
    return {'native_task_id':n['native_task_id'],'native_product_key':n['native_product_key'],'native_content_digest':n['native_content_digest'],
            'source_work_sha256':packet['parent_pdf_sha256'],'excerpt_pdf_sha256':packet['source_pdf_sha256'],'segments':segs}


def anchor(vid,pointer,quote,views):
    packet,v,path=views['gs120-recovered-source-'+str(vid)]
    pieces=[p for p in v['native_context']['pieces'] if p.get('item_ref')==pointer and p['source_field']=='text']
    assert len(pieces)==1
    piece=pieces[0];item=next(x for x in v['native_context']['items'] if x['self_ref']==pointer)
    assert item['text'].count(quote)==1,(vid,pointer,quote)
    local=item['text'].index(quote);s=piece['start']+local;e=s+len(quote)
    assert v['passage']['text'][s:e]==quote
    pages={p['excerpt_physical_page']:p['parent_physical_page'] for p in packet['page_map']}
    return {'passage_id':v['passage']['passage_id'],'start':s,'end':e,'text':quote,
            'native':endpoint({'passage_id':v['passage']['passage_id'],'start':s,'end':e,'text':quote},views),
            'packet':pin(path),'native_pointer':pointer,'native_start':local,'native_end':local+len(quote),
            'parent_physical_pages':sorted({pages[p['page_no']] for p in item.get('prov',[])}),
            'original_native_field':item.get('orig'), 'projected_native_field':item['text']}


# Order and semantics independently authored after reading the native source paragraphs.
EXPECTED=[
('fe239c46ce4dfdcb422161f514aa985ccd14162810900df65ab3ee4f7df1ed8c','partial_definition_location_reference',
 'The source explicitly says the binomial distribution was defined in Chapter3. The pair retains a useful definition-location reference; Chapter3 is not literal explanatory/defining content and its contents were not re-inspected.',
 [(110,'#/texts/13','The binomial distribution with parameters n, p, and k was defined in Chapter 3.')],
 'definition_location_reference; keep n,p,k wording and later coin-count description separate from damaged binomial display'),
('d41dddc191db90fef28ed2f539c6b412c2f26b4ff80bf0c4b666bacbfb1f3570','unsupported_definition',
 'Equation5.2 is a formula reference, not defining prose for the later bare distribution occurrence. The local source names the preceding law Poisson and requires nonnegative values summing to1; those relationships are useful separately.',
 [(110,'#/texts/118','The above distribution is the Poisson distribution. We note that it must be checked that the distribution given in Equation 5.2 really is a distribution, i.e., that its values are non-negative and sum to 1. (See Exercise 12.)')],
 'formula_reference to Equation5.2; names preceding law Poisson; source-requested distribution checks remain conditions, not performed proof'),
('1c702871f30b118ebb0a5444e304242ebac0ef2fa3e863bb3e90cd5d15a82dae','unsupported_subject_and_content_role',
 'The named law discusses averages in many cases, then contrasts Cauchy averages that do not approach a specific number. It does not explain the density expression by the law; the corrected subject is average behavior under stated independence/qualification.',
 [(120,'#/texts/113','The Law of Large Numbers, which we will discuss in Chapter 8, states that in many cases, if we take the average of independent values of a random variable, then the average approaches a specific number as the number of values increases. It turns out that if one does this with a Cauchy-distributed random variable, the average does not approach any specific number. ✷')],
 'qualified law statement and Cauchy-average contrast, not density explained-by law or universal convergence'),
('1a82454f3a66996747b8110a2ec6882a317ccb9a81471836f8add0f9058433c5','unsupported_definition_and_direction',
 'The law bolsters the frequency interpretation and motivates interpreting expected value as repeated-experiment average. This is historical justification, not a definition by the law; direction is law→interpretation rationale.',
 [(134,'#/texts/219','With the Law of Large Numbers to bolster the frequency interpretation of probability, we find it natural to justify the definition of expected value in terms of the average outcome over a large number of repetitions of the experiment.')],
 'historical_interpretive_justification, with average-outcome content explicitly retained'),
('daabc26168455c027b8b01daaff018b813c0167bd31217ccde31720e400de0f4','unsupported_general_explanation_scope',
 'Chapter8 is a forward reference for making the average-concentration statement precise. Local prose explains spread around the mean and finite-variance independent-trial shrinkage, so a generic standard-deviation→chapter explanation loses the actual subject and conditions.',
 [(139,'#/texts/144','Since the standard deviation tells us something about the spread of the distribution around the mean, we see that for large values of n, the value of An is usually very close to the mean of An, which equals µ, as shown above. This statement is made precise in Chapter 8, where it is called the Law of Large Numbers.')],
 'forward_reference_for_precision of the concentration statement; finite variance/independent trials remain enclosing premises'),
('0d0ed4685faa19f8eadb3e8c8e88e5a1455ee1a741cdbc9b24831d0c9755810f','supported_partial_explanatory_application_reference',
 'The source explicitly applies Theorem6.15 to the local X uniform on[0,1] variance calculation. The literal pair is a useful partial explanatory application reference; it does not explain arbitrary X or carry the theorem/result/mean conditions.',
 [(142,'#/texts/172','Example 6.25 (continuation of Example 6.20) If X is uniformly distributed on [0, 1], then, using Theorem 6.15, we have')],
 'applied_result_reference for local uniform-X variance calculation; no numerical execution or general-X assertion'),
('345e8d51b5ff3768f7b72014b39582df428be9b4cec545d9ce2b2e7a40f66ca9','unsupported_definition_bibliographic_content',
 'Epstein is a more-realistic discussion of the simplified problem, not defining content for opening bid. A separate explicit local characterization says a player with point count13 or more has an opening bid.',
 [(149,'#/texts/64','A player with a point count of 13 or more is said to have an opening bid.'),
  (149,'#/texts/68','A more realistic discussion of this problem can be found in Epstein, The Theory of Gambling and Statistical Logic.1 ✷')],
 'opening_bid local threshold characterization separate from problem-level further-discussion bibliography'),
('debaf86e775b4e18d4b1b8ce68cf63b323e325e9cc37da324d5aa8daa3ba9a73','unsupported_definition_bibliographic_scope',
 'The source referral is for this simplified bridge point-count/opening-bid problem. It does not define hand in the cited book; exact hand occurrence lies in the13-independent-trials approximation with an explicit caveat.',
 [(149,'#/texts/64','Let us regard the total hand of 13 cards as 13 independent trials with this common distribution. (Again this is not quite correct because we assume here that we are always choosing a card from a full deck.)'),
  (149,'#/texts/68','A more realistic discussion of this problem can be found in Epstein, The Theory of Gambling and Statistical Logic.1 ✷')],
 'further_discussion_source for this problem, not hand defined-by book'),
('f0aa69b0a73774a0254bc2ada57421833b86133e0906e02875af098e4826ce33','unsupported_definition_wrong_subject',
 'The program is used to compute the distribution of point countC for a hand under a single-card common law and n=13 approximation. It does not define hand. Preserve fused literal programNFoldConvolution and the explicit full-deck/independence caveat.',
 [(149,'#/texts/64','Then the distribution for the point count C for the hand can be found from the programNFoldConvolution by using the distribution for a single card and choosing n = 13.')],
 'computed_using(distribution of point countC,programNFoldConvolution), conditional on single-card law and n=13 approximation'),
]


def main():
    manifest=read(PREFIX+'manifest.json');assert manifest['run']['id']==161 and manifest['run']['sealed'] and manifest['run']['status']=='finished'
    new=packets('source-recovery/attempt001/source-packets');old=packets('source-packets')
    named=read('assessment/run160-final-named001/task-800.json')['body']['structural_product']
    task=read(PREFIX+'task-1069.json');model=task['body']['structural_product'];cs=model['definition_components']['components']
    assert model['inputs']==named['inputs']
    assert cs[:35]==named['definition_components']['components'] and len(cs)==44
    assert [x['component_id'] for x in cs[35:]]==[x[0] for x in EXPECTED]
    baseline=read('authors/output-definition-review/c/adjudicated-assessment.json')['entries']
    def identity(comp,views):return {'interpretation':comp['interpretation'],'term':endpoint(comp['term'],views),'content':endpoint(comp['content'],views)}
    baselines={b['component_id']:identity(b['frozen_component'],old) for b in baseline}
    crosswalk=[]
    for i,b in enumerate(baseline):
        ids=[c['component_id'] for c in cs if identity(c,new)==baselines[b['component_id']]]
        assert len(ids)==1
        crosswalk.append({'baseline_component_id':b['component_id'],'model_component_ids':ids,'exact_native_pair':baselines[b['component_id']],
            'baseline_authority':pin('authors/output-definition-review/c/adjudicated-assessment.json')|{'json_pointer':f'/entries/{i}'},
            'meaning_policy':'Exact old/current original-work/native leaf/offset correspondence is authenticated. C re-read source context; semantics are independently stated below, not inferred from identical IDs/counts.'})
    additions=[]
    for comp,(cid,state,reason,quotes,meaning) in zip(cs[35:],EXPECTED,strict=True):
        additions.append({'component_id':cid,'actual_component':comp,'actual_ordinal':36+len(additions),
            'actual_endpoint_native_identity':identity(comp,new),'C_state':state,'C_reason':reason,
            'corrected_or_retained_source_alternatives':[anchor(*q,new) for q in quotes],
            'expected_local_meaning':meaning,'baseline_exact_matches':[x['baseline_component_id'] for x in crosswalk if cid in x['model_component_ids']],
            'facets':{'location':'exact_source_and_native_coordinates','role':state,'attachment':'source-local relation independently explained in C_reason',
                      'condition_scope':meaning,'recognition':'Literal source preserved; damaged neighboring displays not repaired or equated to clean content.',
                      'completeness':'unassessed_whole_case_and_report'},
            'public_credit':'not_requested_or_established; private proposal only'})
    inventories=[];report_rows=[];native_rows=[];coverage=Counter();diagnostics=Counter();execution=Counter();rawparse=Counter();native_states=Counter()
    annotation_errors=[]
    for t in manifest['tasks']:
        path=PREFIX+t['raw_file'];actual=pin(path);assert actual['sha256']==t['raw_sha256']
        envelope=read(path);assert envelope['status']=='done' and envelope['has_task_result'] and not envelope['has_task_error']
        b=envelope['body'];detail=source_python(b['parse_detail']);
        for c in b['coverage']:coverage[(t['method'],c['family'],c['outcome'])]+=1
        errors=detail.get('annotation_errors',[]);annotation_errors.extend({'task':t['selected_task_id'],'error':x} for x in errors)
        inv={'task':t,'raw':actual,'body_outcome':b['outcome'],'annotation_errors':errors,
             'detail_keys':list(detail),'coverage':b['coverage'],'execution':detail.get('execution',[]),
             'record_interpretation':detail.get('record_interpretation',[]),'record_policy_events':detail.get('record_policy_events',[])}
        for x in detail.get('execution',[]):execution[(x.get('family'),x.get('outcome'),x.get('reason'))]+=1
        inventories.append(inv)
        for ri,report in enumerate(detail.get('reports',[])):
            if 'report' not in report:
                for g in report.get('groups',[]):
                    for field in g.get('fields',[]):native_states[(report['family'],field.get('role'),field.get('state'),field.get('reason'))]+=1
                native_rows.append({'task_id':t['selected_task_id'],'source_view_id':t['unit_id'],'raw':actual,'report_index':ri,'report':report,
                    'meaning':'Native-structure content/recognition states retained separately from model raw-JSON parsing; no semantic support inferred.'})
                continue
            rep=report['report'];raw=rep['raw_json'];state='parsed';failure=None
            try:parsed=json.loads(raw)
            except (ValueError,TypeError) as exc:parsed=None;state='failed';failure=str(exc)
            rawparse[state]+=1
            for d in report['diagnostics']:diagnostics[(report['family'],d.get('code'),d.get('role'))]+=1
            for d in report['association_diagnostics']:diagnostics[(report['family'],'association:'+str(d.get('code')),d.get('role'))]+=1
            report_rows.append({'task_id':t['selected_task_id'],'source_view_id':t['unit_id'],'raw':actual,'report_index':ri,
                'context':report['context'],'family':report['family'],'context_digest':rep['context_digest'],'computation':rep['computation'],
                'raw_json_sha256':hashlib.sha256(raw.encode()).hexdigest(),'parse_state':state,'parse_failure':failure,
                'top_level_keys':list(parsed) if isinstance(parsed,dict) else None,
                'diagnostics':report['diagnostics'],'association_diagnostics':report['association_diagnostics'],
                'semantic_content':'unassessed except independently source-reviewed final44 components; parsed JSON or producer scores never establish supported meaning'})
    source=read('assessment/final-source-capture/source-capture-assessment.json');case_model=[]
    for c in source['cases']:
        intersections=[]
        for a in additions:
            for role in ['term','content']:
                p=a['actual_component'][role]
                if any(s['passage_id']==p['passage_id'] and s['start']<p['end'] and s['end']>p['start'] for an in c['exact_source_correspondence']['anchors'].values() for s in an['segments']):
                    intersections.append({'component_id':a['component_id'],'role':role})
        assert not intersections or c['case_id']=='GS120-COMMON-003'
        case_model.append({'case_id':c['case_id'],'named35_semantic_state':c['named'],
            'model44_semantic_state': 'partial_context_reference_core_formula_not_captured' if intersections else c['named']['state'],
            'new_addition_location_intersections':intersections,
            'C_judgment':'The new Chapter3 reference is useful source context but does not supply the selected damaged b(n,p,k) formula roles or repair its coefficient.' if intersections else 'Existing35 components are literally unchanged under identical source inputs, so existing independently authored source/role/condition/fidelity judgments apply; no model addition expresses this source case.',
            'other_provider_candidates':'unassessed as semantic captures; retained with parse/content diagnostics in provider inventory',
            'whole_case_capture':False,'source_expectation_authority':c['source_authority']})
    write('model161-assessment.json',{'protocol':'gs120-final-model-C-source-adjudication-1','date':'2026-11-06','manifest':pin(PREFIX+'manifest.json'),
        'run':manifest['run'],'completed':manifest['completed_result'],'model_components':44,'named_components_exactly_unchanged':35,
        'full_structural_inputs_equal':True,'raw_effective_version_shape':'All raw components omit effective_version; frozen ordinary inspection adds explicit null. No serialization equality is claimed across those representations.',
        'independent_author_exposure':'C previously reviewed baseline9/current35/common32/extra32 and A/B; re-read each new component source/native paragraph before this adjudication. Exposed development, no held-out claims.',
        'additions':additions,'baseline9_native_crosswalk':crosswalk,'source64_cases':case_model,
        'conclusion':'The model retains the35 existing components plus9 reference-heavy additions: one supported partial local theorem-application explanation, one useful definition-location reference with interpretation limits, and7 unsupported exact subject/content/type pairs with useful corrected relations. This increases retained proposals, not established complete knowledge, scientific truth or general efficacy.',
        'whole_report_completeness':'unassessed','scientific_truth':'unassessed','probability_calibration':'unassessed','public_publication':'not_requested_for_new_model_components'})
    write('model161-provider-inventory.json',{'protocol':'gs120-final-model-provider-content-inventory-C-1','manifest':pin(PREFIX+'manifest.json'),
        'checkpoint_verification':pin('gliner25-current161-verification.json'),'tasks':inventories,'reports':report_rows,'native_structure_reports':native_rows,
        'task_counts':dict(Counter(t['method'] for t in manifest['tasks'])),'raw_report_parse_outcomes':dict(rawparse),
        'annotation_errors':annotation_errors,
        'coverage_counts':[{'method':k[0],'family':k[1],'outcome':k[2],'count':v} for k,v in sorted(coverage.items())],
        'diagnostic_counts':[{'family':k[0],'code':k[1],'role':k[2],'count':v} for k,v in sorted(diagnostics.items(),key=lambda x:str(x[0]))],
        'execution_counts':[{'family':k[0],'outcome':k[1],'reason':k[2],'count':v} for k,v in sorted(execution.items(),key=lambda x:str(x[0]))],
        'native_content_state_counts':[{'family':k[0],'role':k[1],'state':k[2],'reason':k[3],'count':v} for k,v in sorted(native_states.items(),key=lambda x:str(x[0]))],
        'limits':'All97 accepted envelopes retained, including unresolved/unsupported/unlocated/partial content states. Parse success and done task do not certify content. Other raw provider groups/fields remain semantically unassessed and are not dropped or counted as supported captures. Native model scores are uncalibrated decoder output.'})
    write('model161-input-pins.json',{'inputs':[pin(p) for p in sorted(PINS|{'assessment/final-source-capture/build_model_assessment.py'})]})
    print(json.dumps({'components':len(cs),'unchanged':35,'additions':len(additions),'baseline_exact_native_pairs':len(crosswalk),'tasks':len(inventories),'raw_provider_reports':len(report_rows),'native_structure_reports':len(native_rows),'raw_parse':dict(rawparse),'annotation_errors':len(annotation_errors)}))


if __name__=='__main__':main()
