#!/usr/bin/env python3
"""Read-only frozen current-output, source-pin and verdict-transport validator."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
GS = HERE.parents[2]
EVIDENCE = GS.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def ptr(value,path):
    for token in path.strip('/').split('/'):
        value = value[int(token)] if isinstance(value,list) else value[token]
    return value

def main():
    ap = HERE/'assessment.json'
    a = json.loads(ap.read_text())
    checks = []
    def check(ok,label):
        checks.append({'passed':bool(ok),'check':label})
    for f in a['frozen_files']:
        p = EVIDENCE/f['path']
        check(p.is_file() and sha(p)==f['sha256'],'frozen hash '+f['path'])
        check(p.is_file() and p.stat().st_size==f['bytes'],'frozen bytes '+f['path'])
    actual = json.loads((GS/'current-extraction/named001/structural-inspection.json').read_text())
    task = json.loads((GS/'assessment/run152-current-named001/task-605.json').read_text())
    report = actual['reports'][0]
    cs = report['definition_components']['components']
    check({k:actual[k] for k in a['product_identity']}==a['product_identity'],'current product identity')
    check(actual['run_id']==152 and actual['cut_id']==204 and actual['task_ids']==[605],'run152 cut204 task605')
    check({k:v for k,v in task.items() if k!='body'}==a['task_identity'],'task registration identity')
    check({k:task['body'][k] for k in a['task_body_identity']}==a['task_body_identity'],'task input/config/release/body identities')
    check(task['status']=='done' and task['has_task_result'] and not task['has_task_error'],'actual task result done')
    # Raw task serialization omits optional None fields that inspection renders as null.
    raw_product=json.loads(json.dumps(task['body']['structural_product']))
    for component in raw_product['definition_components']['components']:
        component.setdefault('effective_version',None)
    for passage in raw_product['inputs']['passages']:
        passage.setdefault('effective_version',None)
        passage.setdefault('parent',None)
    check(raw_product['definition_components']==report['definition_components'],'task components/stages identical after explicit optional-null representation reconciliation')
    check(raw_product['inputs']==report['inputs'],'task input pins identical after explicit optional-null representation reconciliation')
    check(len(cs)==len(a['entries'])==35,'all35 actual current components assessed')
    check(len({c['component_id'] for c in cs})==35,'35 unique current IDs')
    check([c['component_id'] for c in cs]==[e['component_id'] for e in a['entries']],'exact current IDs and order')
    packets = {}
    views = {}
    for f in a['frozen_files']:
        if '/source-recovery/attempt001/source-packets/grinstead-snell-physical' in f['path']:
            p = EVIDENCE/f['path'];s=json.loads(p.read_text());packets[f['path']]=s
            for j,v in enumerate(s['views']):
                views[v['passage']['passage_id']] = (f['path'],j,v)
    check(len(views)==len(report['inputs']['sources'])==len(report['inputs']['passages'])==48,'48 recovered pinned source views')
    for passage in report['inputs']['passages']:
        _,_,v=views[passage['passage_id']]
        check(v['passage']==passage,'complete source passage matches report '+passage['passage_id'])
        check(v['source'] in report['inputs']['sources'],'source pin matches current report '+passage['passage_id'])
    pages = sorted({n for s in packets.values() for n in s['parent_physical_pages']})
    check(pages==list(range(191,311))==a['source_scope']['parent_physical_pages'],'120 physical page selection')
    oldpath=EVIDENCE/'2026-11-06_wce-definition-refinement/assessment/b/assessment.json'
    old=json.loads(oldpath.read_text());oldentries={e['component_id']:e for e in old['entries']}
    transported = endpoint_count = quote_count = overlap_count = 0
    newids=[]
    for e,c in zip(a['entries'],cs):
        check(e['original_component']==c,'actual component preserved '+e['assessment_case_id'])
        check(ptr(actual,e['actual_pointer'])==c,'actual current pointer '+e['assessment_case_id'])
        name,j,v=views[c['term']['passage_id']]
        check(e['source_packet']==name and e['source_view_index']==j,'current packet/view mapping '+e['assessment_case_id'])
        check(e['current_source_pin']==v['source'] and v['source'] in report['inputs']['sources'],'complete current pin mapping '+e['assessment_case_id'])
        check(e['native_view']==v['native_view'] and e['source_health_as_reported']==v['native_context']['health'],'native identity and health preserved')
        check(set(e['facets'])=={'term_defined_subject','content_role','direction_attachment','interpretation_type','scope_conditions','recognition_fidelity_to_native'},'six facets '+e['assessment_case_id'])
        check(all(f['verdict'] in {'supported','unsupported','ambiguous','unassessed'} for f in e['facets'].values()),'separate facet vocabulary')
        for role in ['term','content']:
            s=c[role]
            check(s['passage_id']==v['passage']['passage_id'] and v['passage']['text'][s['start']:s['end']]==s['text'],'actual endpoint quote '+role+' '+e['assessment_case_id'])
            endpoint_count+=1
        if 'transport_authentication' in e:
            tr=e['transport_authentication'];oe=oldentries[tr['prior_component_id']];op=EVIDENCE/tr['prior_source_packet'];os=json.loads(op.read_text());ov=os['views'][tr['prior_source_view_index']]
            check(oe['assessment_case_id']==tr['prior_assessment_case_id'],'prior assessor case identity')
            check(e['facets']==oe['facets'],'prior six judgments transported without silent change')
            check(ov['source']==tr['prior_source_pin'],'prior source pin preserved')
            check(ov['passage']['text']==v['passage']['text'],'complete old/current passage identical')
            check(ov['native_context']==v['native_context'],'complete old/current native context identical')
            check(sha256text(v['passage']['text'])==tr['passage_text_sha256'],'transport passage hash')
            check(canonical(v['native_context'])==tr['native_context_canonical_sha256'],'transport native context hash')
            for k in ['native_task_id','native_product_key','native_content_digest']:
                check(ov['source'][k]==v['source'][k]==tr['stable_native_product_fields'][k],'stable native product '+k)
            diffs={k:{'prior':ov['source'].get(k),'current':v['source'].get(k)} for k in set(ov['source'])|set(v['source']) if ov['source'].get(k)!=v['source'].get(k)}
            check(diffs==tr['changed_pin_fields'],'changed recipe/projection/run/release/cut/view pins recorded')
            check('recipe_digest' in diffs,'recipe digest difference not hidden')
            for role in ['term','content']:
                check(tr['endpoint_correspondence'][role]=={'prior':oe['original_component'][role],'current':c[role]},'endpoint correspondence preserved')
                check({k:x for k,x in oe['original_component'][role].items() if k!='passage_id'}=={k:x for k,x in c[role].items() if k!='passage_id'},'endpoint offsets and text identical across views')
            transported+=1
        else:
            newids.append(c['component_id'])
        for q in e['expected_source_quotes']:
            s=packets[q['packet']];qv=s['views'][q['view_index']]
            check(qv['passage']['passage_id']==q['passage_id'] and qv['source']['source_view_id']==q['source_view_id'],'expected quote source identity')
            check(qv['passage']['text'][q['start']:q['end']]==q['text'],'independently expected source quote exact')
            quote_count+=1
            for n in q['native_overlaps']:
                pc=ptr(s,n['piece_pointer']);it=ptr(s,n['item_pointer'])
                check(pc==n['piece'] and pc['item_ref']==n['native_pointer'],'exact current projection piece/pointer')
                check(qv['passage']['text'][pc['start']:pc['end']]==it[n['source_field']],'native piece source field exact')
                check(it[n['source_field']][n['converted_start']:n['converted_end']]==n['text'],'native-relative expected quotation')
                check(qv['passage']['text'][n['passage_start']:n['passage_end']]==n['text'],'passage-relative expected quotation')
                check(it.get('orig')==n['original_item_text'] and it.get('text')==n['converted_item_text'],'original and converted native text preserved separately')
                parent=next(it for it in qv['native_context']['items'] if it.get('self_ref')==n['native_pointer'])
                check(parent.get('prov',[])==n['provenance'],'native original provenance preserved')
                check([s['page_map'][pr['page_no']-1]['parent_physical_page'] for pr in parent.get('prov',[])]==n['parent_physical_pages'],'native physical page correspondence')
                overlap_count+=1
    check(transported==32 and len(newids)==3,'32 authenticated transports and3 new independent readings')
    check(newids==a['comparison']['new_independent_component_ids'],'three new exact IDs')
    failures=[c for c in checks if not c['passed']]
    receipt={'protocol':'independent-current-named-b-validation-1','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':'uv run python docs/design_review/evidence/2026-11-06_wce-gs120/authors/current-named-review/b/validate.py','outcome':'failed' if failures else 'passed','read_only':True,'assessment_sha256':sha(ap),'validator_sha256':sha(Path(__file__).resolve()),'frozen_input_file_count':len(a['frozen_files']),'current_components':35,'current_source_views':48,'physical_pages':len(pages),'authenticated_transports':transported,'new_independent_readings':len(newids),'actual_endpoint_quotes':endpoint_count,'expected_source_quotes':quote_count,'native_piece_correspondences':overlap_count,'checks':len(checks),'failures':failures,'scope':'Frozen run152/task605 output identity, exact current source pins/quotes/native mapping and declared prior semantic-verdict transport only. Not mathematical truth, PDF fidelity, corpus completeness, held-out quality, provider qualification or publication permission.'}
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return int(bool(failures))

def sha256text(text):
    return hashlib.sha256(text.encode()).hexdigest()

if __name__=='__main__':
    sys.exit(main())
