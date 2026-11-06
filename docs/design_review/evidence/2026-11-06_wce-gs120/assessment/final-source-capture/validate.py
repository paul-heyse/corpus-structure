"""Literal/hash/native-coordinate checks; independent authored meanings are not a test oracle."""
from datetime import datetime, timezone
from functools import cache
import hashlib
import json
import math
from pathlib import Path

from corpus_structure.semantic.observations import source_python

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
checks=[]


def check(value,label):
    checks.append({'passed':bool(value),'check':label})


@cache
def read(path):
    return json.loads((ROOT/path).read_text())


@cache
def sha(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


@cache
def lines(path):
    with (ROOT/path).open() as f:
        return [json.loads(line) for line in f]


def literal_leaf(view,seg):
    item=next(x for x in view['native_context']['items'] if x['self_ref']==seg['native_pointer'])
    if seg['source_field']=='cell_text':
        return item['data']['table_cells'][seg['cell_index']]['text']
    return item[seg['source_field']]


def main():
    prefix='assessment/final-source-capture/'
    pins=read(prefix+'input-pins.json')
    for item in pins['inputs']+pins['frozen_scoped_exports']:
        check(sha(item['path'])==item['sha256'],'exact input hash '+item['path'])
    assessment=read(prefix+'source-capture-assessment.json')
    original_case_hash=(HERE/'source64-before-downstream-editorial-sha256.txt').read_text().strip()
    check(hashlib.sha256(json.dumps(assessment['cases'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==original_case_hash,'all64 existing C case objects unchanged by downstream editorial integration')
    common=read('authors/c/source-adjudication/adjudicated-source-cases.json')['cases']
    extra=read('authors/c/source-recovery-assessment/source-cases.json')['cases']
    originals={x['id']:x for x in common+extra}
    check(len(assessment['cases'])==64,'all64 source cases')
    check({c['case_id'] for c in assessment['cases']}==set(originals),'all exact source case identities')
    old_views={}
    for p in (ROOT/'source-packets').glob('grinstead*.json'):
        packet=json.loads(p.read_text())
        for view in packet['views']:
            old_views[view['native_view']['id']]=(packet,view)
    candidates=read(prefix+'candidate-locations.json')['cases']
    for i,c in enumerate(assessment['cases']):
        original=originals[c['case_id']];loc=candidates[i]
        check(c['source_expectation']==original,c['case_id']+' frozen full expectation retained')
        check(c['case_id']==loc['case_id'],c['case_id']+' exact candidate address')
        check(c['independent_source_authors']==(['A','B','C'] if i<32 else ['C']),c['case_id']+' author exposure frame')
        check(c['model']['state'].startswith('unassessed') or (c['model']['state']=='bounded_final_model44_assessed_other_provider_fields_unassessed' and not c['model']['assessment']['whole_case_capture']),c['case_id']+' no automatic whole model credit')
        check(c['named']['positive_whole_case_capture'] is False,c['case_id']+' no automatic whole-case positive')
        check(len(c['facets'])==6,c['case_id']+' six separate source-capture facets')
        if i<32:
            oldpacket,oldview=old_views[original['source_view_id']]
        for name,a in c['exact_source_correspondence']['anchors'].items():
            origanchor=original['anchors'][name]
            if i<32:
                _,ov=old_views[origanchor.get('source_view_id',original['source_view_id'])]
                s,e=origanchor['span']
                if origanchor.get('coordinate_space','passage_text')=='native_item_text':
                    oi=next(x for x in ov['native_context']['items'] if x['self_ref']==origanchor['native_pointer'])
                    check(oi['text'][s:e]==origanchor['quote'],c['case_id']+'/'+name+' old native-only quote')
                else:
                    check(ov['passage']['text'][s:e]==origanchor['quote'],c['case_id']+'/'+name+' old projected quote')
            for seg in a['segments']:
                packet=read(seg['packet']);view=next(x for x in packet['views'] if x['native_view']['id']==seg['source_view_id'])
                check(sha(seg['packet'])==seg['packet_sha256'],c['case_id']+'/'+name+' recovered packet hash')
                check(view['passage']['passage_id']==seg['passage_id'],c['case_id']+'/'+name+' exact passage ID')
                check(view['passage']['text'][seg['start']:seg['end']]==seg['text'],c['case_id']+'/'+name+' recovered quote')
                check(literal_leaf(view,seg)[seg['native_start']:seg['native_end']]==seg['text'],c['case_id']+'/'+name+' exact native field/local offset quote')
                n=view['native_view']
                check(seg['source_identity']==[n['native_task_id'],n['native_product_key'],n['native_content_digest']],c['case_id']+'/'+name+' immutable native identity')
                check(seg['source_work_sha256']==packet['parent_pdf_sha256'],c['case_id']+'/'+name+' original source-work hash')
                check(seg['excerpt_pdf_sha256']==packet['source_pdf_sha256'],c['case_id']+'/'+name+' excerpt source hash')
                check(bool(seg['parent_physical_pages']),c['case_id']+'/'+name+' parent physical pages explicit')
                if i<32:
                    check(oldpacket['parent_pdf_sha256']==packet['parent_pdf_sha256'] and oldpacket['source_pdf_sha256']==packet['source_pdf_sha256'],c['case_id']+'/'+name+' unchanged original source-work bytes old→current')
                    on=ov['native_view']
                    check(seg['source_identity']==[on['native_task_id'],on['native_product_key'],on['native_content_digest']],c['case_id']+'/'+name+' old→current immutable product identity')
                    check(literal_leaf(ov,seg)==literal_leaf(view,seg),c['case_id']+'/'+name+' whole original native field bytes unchanged')
                    check(literal_leaf(ov,seg)[seg['native_start']:seg['native_end']]==seg['text'],c['case_id']+'/'+name+' old→current exact native pointer and local offsets')
            for gap in a.get('gaps',[]):
                item=next(x for x in ov['native_context']['items'] if x['self_ref']==gap['native_pointer'])
                check(item['text'][gap['native_start']:gap['native_end']]==gap['text'],c['case_id']+'/'+name+' native-only unprojected quote retained')
        for p in loc['scoped_participant_candidates']+loc['scoped_edge_candidates']:
            row=lines(p['file'])[p['line']-1]
            check(row['population']=='interpretation' and row['row']['contribution_id']==p['contribution_id'],c['case_id']+' exact scoped file/line/contribution')
            check(source_python(row['row']['value'])==p['value'],c['case_id']+' scoped retained value unchanged')
    gaps=[(c['case_id'],name) for c in assessment['cases'] for name,a in c['exact_source_correspondence']['anchors'].items() if a['state']=='native_coordinate_gap']
    check(gaps==[('GS120-COMMON-013','observed_caption'),('GS120-COMMON-013','expected_caption')],'two exact native-only caption gaps preserved')
    rawold=read('assessment/run152-current-named001/task-605.json')['body']['structural_product']
    rawnew=read('assessment/run160-final-named001/task-800.json')['body']['structural_product']
    check(rawold==rawnew,'whole raw152→160 report literal identity')
    receipt=read('assessment/run160-exact-transport001.json')
    for item in receipt['inputs']:
        p=str(Path(item['path']).relative_to(ROOT)) if Path(item['path']).is_absolute() else item['path'].split('2026-11-06_wce-gs120/',1)[-1]
        check(sha(p)==item['sha256'],'root-authenticated raw task hash '+p)
    for a in read(prefix+'table-note-assessment.json')['audits']:
        check(a['source_expectation']==originals[a['case_id']],'table/note exact source expectation '+a['case_id'])
        for e in a['selected_edges']:
            check(e['value']['subject_id'] in e['value']['dependencies'] and e['value']['target_id'] in e['value']['dependencies'],'table attachment retained endpoints')
            check(e['value']['relation'] in ['header','row_label'],'table relation orientation explicit')
    for b in read(prefix+'policy-band-assessment.json')['bands']:
        envelope=lines(b['file']['path'])[b['line']-1];v=envelope['payload_json'];v=json.loads(v) if isinstance(v,str) else v
        op=v['body']['contribution_operations'][b['operation_index']];local=op['local_interpretation']
        check(op['operation_key']==b['operation_key'],'policy exact operation key')
        check(local['outcome']==b['outcome'] and local.get('request_digest')==b['request_digest'] and local.get('result_digest')==b['result_digest'],'policy exact outcome and request/result identity')
        if b['potentials'] is not None:
            q=source_python(local['request'])
            check(q['potentials']==b['potentials'] and q['dependence_scopes']==b['dependence_scopes'],'policy actual assumptions retained')
            check(q['constraints']==[] and q['dependence_scopes']==[],'selected bands no extra constraint/dependence assertions')
            unary=[p for p in q['potentials'] if len(p['scope'])==1]
            check(all(p['values']==[0.0,0.0] for p in unary),'selected uniform unary assumptions retained')
            if b['phase']=='review-coupled':
                shared=[p for p in q['potentials'] if len(p['scope'])>1]
                check(len(shared)==1 and shared[0]['values'][0]==math.log(2) and shared[0]['values'][-1]==math.log(2) and all(v==0 for v in shared[0]['values'][1:-1]),'coupled symmetric all/none bonus is explicit policy assumption')
            else:
                check(len(unary)==len(q['potentials']),'independent arms have no joint preference')
    for a in read(prefix+'artifact-occurrence-assessment.json')['occurrences']:
        row=lines(a['file']['path'])[a['line']-1]['row']
        check(row['contribution_id']==a['contribution_id'] and source_python(row['value'])==a['value'],'artifact exact occurrence file/line/value')
        check(a['value']['revision_state']=='unknown' and a['value']['aliases']==[],'artifact unknown revision and no invented aliases')
    contexts=read(prefix+'contextual-attachment-assessment.json')['edges']
    check(len(contexts)==14,'all14 actual contextual selected edges')
    for e in contexts:
        row=lines(e['file']['path'])[e['line']-1]['row']
        check(row['contribution_id']==e['contribution_id'] and source_python(row['value'])==e['actual_relationship'],'contextual actual private edge literal')
        check(e['component_reference']['run_id']==160 and e['component_reference']['cut_id']==210 and e['component_reference']['origin_task_id']==800,'contextual original producer custody')
        check(e['witness_support']=='unassessed_actual_workflow','contextual witness not silently promoted')
    policy=read(prefix+'policy-band-assessment.json')
    check(policy['independent_population_check']['same8210_contribution_ids'] and policy['independent_population_check']['same84_operation_cohorts_and_choices'],'exact matched policy populations/cohorts')
    failures_account=read(prefix+'downstream-failure-account.json')
    check(failures_account['failures']['artifact_native_ABI']['evidence']['completed_artifact_result'] is False,'artifact failed attempt no accepted product')
    check(failures_account['failures']['dossier_native_timeout']['evidence']['accepted_task_results']==0,'dossier failed attempt no accepted result')
    outputs=['source-capture-assessment.json','policy-band-assessment.json','table-note-assessment.json','artifact-occurrence-assessment.json','contextual-attachment-assessment.json','downstream-failure-account.json','input-pins.json','judgments.py','build_assessment.py','prepare_candidates.py','validate.py','README.md','source64-before-downstream-editorial-sha256.txt']
    artifact_links=read(prefix+'artifact-link-assessment.json')
    outputs += ['artifact-link-assessment.json','assess_downstream.py']
    for item in artifact_links['inputs']:
        check(sha(item['path'])==item['sha256'],'artifact-link exact input hash '+item['path'])
    pilot=read(artifact_links['inputs'][0]['path'])['reports'][0]['artifact_identity']
    check(artifact_links['run_id']==183 and artifact_links['cut_id']==247 and artifact_links['task_ids']==[1070],'artifact exact completed producer')
    check(len(pilot['records'])==142 and len(pilot['pairs'])==116,'actual artifact pilot population')
    for case in artifact_links['cases']:
        pair=pilot['pairs'][case['pair_index']]
        check((pair['left'],pair['right'],pair['model_probability'])==(case['left_id'],case['right_id'],case['model_probability']),'artifact exact assessed pair and score')
        check(pair['revision_relation']=='unknown' and pair['standing']=='candidate_relative_private','artifact unknown revision/private standing retained')
    check(artifact_links['judgment_counts']=={'unsupported_as_same_artifact_retained_lexical_alternative':4,'supported_partial_source_artifact_lineage_candidate':7},'bounded authored artifact frame counts')
    dossier_path=prefix+'dossier-selection-assessment.json'
    if (ROOT/dossier_path).is_file():
        dossiers=read(dossier_path)
        outputs.append('dossier-selection-assessment.json')
        for item in dossiers['inputs']:
            check(sha(item['path'])==item['sha256'],'dossier exact input hash '+item['path'])
        full=[read(p['input']['path'])['reports'][0]['dossier'] for p in dossiers['policies']]
        check(full[0]['members']==full[1]['members'],'both complete actual dossier member objects equal')
        check(full[0]['supported_facets']==full[1]['supported_facets'],'both actual dossier supported facet objects equal')
        check(dossiers['full_members']==8280 and dossiers['scoped_source_members']==8210 and dossiers['named_role_members']==70,'actual dossier population grains')
        check(dossiers['distinct_protected_assertions']==2 and len(dossiers['supported_role_facets'])==4,'four role facets do not become four independent assertions')
        for summary,product in zip(dossiers['policies'],full):
            representation=product['representation']
            check(summary['represented_facets']==representation['represented_facets'] and summary['missing_facets']==representation['missing_facets'],'actual dossier represented/missing facets')
            check(summary['selected_count']==12 and summary['omitted_count']==8268 and len(product['members'])==8280,'display omission preserves full dossier membership')
            members_by_id={m['member_id']:m for m in product['members']}
            check(summary['selected_ids']==representation['selected'],'actual dossier representative order retained')
            check(summary['selected_members']==[members_by_id[key] for key in representation['selected']],'all actual selected member objects retained in display order')
    failures=[x for x in checks if not x['passed']]
    result={'protocol':'gs120-final-source-capture-literal-validation-1','timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'outcome':'failed' if failures else 'passed','command':'uv run python docs/design_review/evidence/2026-11-06_wce-gs120/assessment/final-source-capture/validate.py',
        'check_count':len(checks),'failures':failures,'source_cases':64,'input_pins':len(pins['inputs']),
        'artifact_hashes':{f:sha(prefix+f) for f in outputs},
        'establishes':'Input bytes, exact frozen-case transcription, source/native-coordinate bridges and exact output citations; authored semantic judgments remain independently reviewable.',
        'does_not_establish':'Source completeness, scientific truth, full-corpus efficacy, probability calibration, model quality, public authority or agreement by nonexistent reviewers.'}
    (HERE/'validation-receipt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['artifact_hashes']},ensure_ascii=False))
    return int(bool(failures))


if __name__=='__main__':
    raise SystemExit(main())
