#!/usr/bin/env python3
"""Read-only identity/quotation validator; no inference or semantic correctness test."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parents[2]
BASE = HERE.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def pointer(value, path):
    for token in path.strip('/').split('/'):
        value = value[int(token)] if isinstance(value,list) else value[token]
    return value

def main():
    path = HERE / 'assessment.json'
    a = json.loads(path.read_text())
    checks = []
    def check(ok, label):
        checks.append({'passed':bool(ok),'check':label})
    for f in a['input_manifest']:
        p = EVIDENCE / f['path']
        check(p.is_file() and sha(p)==f['sha256'], 'frozen sha256 '+f['path'])
        check(p.is_file() and p.stat().st_size==f['bytes'], 'frozen bytes '+f['path'])
    final = json.loads((BASE/'raw/after004/components.json').read_text())
    after = json.loads((BASE/'raw/after004/result.json').read_text())
    before = json.loads((BASE/'raw/before001/result.json').read_text())
    check(final['named']==after['rules']['current_rules']['components'], 'final named identical to replay result')
    check(final['model']==after['model']['components'], 'final model identical to replay result')
    check(len(final['named'])==32 and len(final['model'])==9 and len(a['entries'])==41, 'all41 assessed with 32named and9model')
    check(sum(c['interpretation']=='definition' for c in final['named'])==13, '13named definition proposals')
    check(sum(c['interpretation']=='explanation' for c in final['named'])==19, '19named explanation proposals')
    check(after['model']['windows']==before['model']['windows']==149,'149windows in each replay report')
    check(before['source_annotation_tasks']==after['source_annotation_tasks'],'same40 annotation task identities')
    check(after['original_sources']==before['original_sources']==40,'same40 original source count')
    check(after['inference']=='not_run' and after['database_writes']=='not_run','replay reports no inference or DB writes')
    originals = before['rules']['current_rules']['components'] + before['model']['components']
    old = {c['component_id']:c for c in originals}
    new = final['named']+final['model']
    check(len({c['component_id'] for c in new})==41,'41 unique actual component IDs')
    check(a['before_after']['unchanged_exact_ids']==[c['component_id'] for c in new if c['component_id'] in old and old[c['component_id']]==c],'unchanged exact IDs recomputed')
    check(len(a['before_after']['unchanged_exact_ids'])==9,'all nine baseline components unchanged exactly')
    check(a['before_after']['added_named_ids']==[c['component_id'] for c in final['named'] if c['component_id'] not in old],'31 added named IDs recomputed')
    check(a['before_after']['added_model_ids']==[c['component_id'] for c in final['model'] if c['component_id'] not in old],'one added model ID recomputed')
    check(a['before_after']['removed_ids']==[c['component_id'] for c in originals if c['component_id'] not in {n['component_id'] for n in new}]==[],'no removed IDs')
    input_refs = []
    for name, wanted in after.get('input_sha256',{}).items():
        p = Path(name)
        actual = sha(p) if p.is_file() else None
        check(actual==wanted,'original replay hash reference '+name)
        input_refs.append({'path':name,'reported_sha256':wanted,'actual_sha256':actual,'outcome':'passed' if actual==wanted else 'failed'})
    packets = {}
    endpoint_count = evidence_count = native_count = 0
    expected_ids = [c['component_id'] for c in new]
    check([e['component_id'] for e in a['entries']]==expected_ids,'assessment order and complete IDs')
    for e in a['entries']:
        c = pointer(final,e['final_pointer'])
        check(e['original_component']==c,'component preserved '+e['assessment_case_id'])
        check(set(e['facets'])=={'term_defined_subject','content_role','direction_attachment','interpretation_type','scope_conditions','recognition_fidelity_to_native'},'six facets '+e['assessment_case_id'])
        check(all(f['verdict'] in {'supported','unsupported','ambiguous','unassessed'} for f in e['facets'].values()),'facet states '+e['assessment_case_id'])
        p = EVIDENCE/e['source_identity']['packet']
        packet = packets.setdefault(str(p),json.loads(p.read_text()))
        v = next(v for v in packet['views'] if v['native_view']['id']==e['source_identity']['native_view']['id'])
        check(e['source_identity']=={'packet':str(p.relative_to(EVIDENCE)),'native_view':v['native_view'],'source':v['source'],'health_as_reported':v['native_context']['health']},'source identity/health '+e['assessment_case_id'])
        for role in ['term','content']:
            s = c[role]
            check(v['passage']['passage_id']==s['passage_id'],'endpoint passage '+e['assessment_case_id']+' '+role)
            check(v['passage']['text'][s['start']:s['end']]==s['text'],'endpoint exact quotation '+e['assessment_case_id']+' '+role)
            endpoint_count += 1
        for q in e['source_evidence']:
            p = EVIDENCE/q['packet']; packet = packets.setdefault(str(p),json.loads(p.read_text()));v=packet['views'][q['view_index']]
            check(v['passage']['passage_id']==q['passage_id'] and v['native_view']['id']==q['source_view_id'],'evidence identity')
            check(v['passage']['text'][q['start']:q['end']]==q['text'],'evidence exact quotation')
            evidence_count += 1
            for n in q['native_overlaps']:
                item = pointer(packet,n['packet_pointer'])
                piece = pointer(packet,n['piece_pointer'])
                check(piece==n['piece'],'native piece preserved')
                check(piece['item_ref']==n['native_item_pointer'],'native reference exact')
                check(v['passage']['text'][piece['start']:piece['end']]==item[n['source_field']],'native projection piece identity')
                check(item[n['source_field']][n['native_text_start']:n['native_text_end']]==n['text'],'native relative quote exact')
                check(v['passage']['text'][n['passage_overlap_start']:n['passage_overlap_end']]==n['text'],'native overlap quote exact')
                check(item.get('orig')==n['orig'] and item.get('text')==n['full_native_text'],'orig and converted native bytes retained')
                parent = next(it for it in v['native_context']['items'] if it.get('self_ref')==n['native_item_pointer'])
                check(parent.get('prov',[])==n['prov'],'native provenance retained')
                check([packet['page_map'][pr['page_no']-1]['parent_physical_page'] for pr in parent.get('prov',[])]==n['parent_physical_pages'],'physical page map exact')
                native_count += 1
    failures = [c for c in checks if not c['passed']]
    receipt = {'protocol':'independent-wce-definition-replay-assessment-b-receipt-1','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':'python docs/design_review/evidence/2026-11-06_wce-definition-refinement/assessment/b/validate.py','outcome':'failed' if failures else 'passed','read_only':True,'assessment_sha256':sha(path),'validator_sha256':sha(Path(__file__).resolve()),'frozen_input_files':len(a['input_manifest']),'component_count':len(a['entries']),'emitted_endpoint_spans':endpoint_count,'source_context_quotes':evidence_count,'native_piece_overlaps':native_count,'checks':len(checks),'original_replay_hash_references':input_refs,'failures':failures,'limits':'Literal validator output. Checks exact identity, spans and native mappings; no semantic truth, completeness, held-out, provider-execution or qualification claim. Implementation/rule hashes are retained as replay-reported, not revalidated against current code.'}
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return int(bool(failures))

if __name__=='__main__':
    sys.exit(main())
