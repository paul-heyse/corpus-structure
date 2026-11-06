"""Authenticate C model assessment literals, native bridges and full raw capture."""
from datetime import datetime, timezone
from functools import cache
import hashlib
import json
from pathlib import Path

from corpus_structure.semantic.observations import source_python

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PREFIX='assessment/final-source-capture/'
checks=[]


def check(value,label):checks.append({'passed':bool(value),'check':label})


@cache
def read(path):return json.loads((ROOT/path).read_text())


def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


@cache
def detail(path):return source_python(read(path)['body']['parse_detail'])


def main():
    data=read(PREFIX+'model161-assessment.json');inv=read(PREFIX+'model161-provider-inventory.json')
    manifest=read(data['manifest']['path'])
    check(manifest['run']['id']==161 and manifest['run']['sealed'] and manifest['run']['status']=='finished','final sealed model161')
    for p in read(PREFIX+'model161-input-pins.json')['inputs']:check(sha(p['path'])==p['sha256'],'model exact input pin '+p['path'])
    for t in manifest['tasks']:
        path='assessment/run161-final-model001/'+t['raw_file'];d=read(path)
        check(sha(path)==t['raw_sha256'] and (ROOT/path).stat().st_size==t['raw_bytes'],'all97 raw envelope bytes '+t['raw_file'])
        check(d['status']=='done' and d['has_task_result'] and not d['has_task_error'],'accepted raw envelope '+t['raw_file'])
    named=read('assessment/run160-final-named001/task-800.json')['body']['structural_product']
    model=read('assessment/run161-final-model001/task-1069.json')['body']['structural_product'];cs=model['definition_components']['components']
    check(cs[:35]==named['definition_components']['components'] and len(cs)==44,'exact35 members retained within44')
    check(named['inputs']==model['inputs'],'complete source structural-input objects equal')
    check(len(data['additions'])==9 and len(data['baseline9_native_crosswalk'])==9,'all9 additions and baseline9 pairs')
    views={}
    for p in (ROOT/'source-recovery/attempt001/source-packets').glob('grinstead*.json'):
        packet=json.loads(p.read_text())
        for v in packet['views']:views[v['passage']['passage_id']]=(packet,v)
    for c,actual in zip(data['additions'],cs[35:],strict=True):
        check(c['actual_component']==actual,'model exact addition '+c['component_id'])
        for role in ['term','content']:
            ep=actual[role];packet,v=views[ep['passage_id']]
            check(v['passage']['text'][ep['start']:ep['end']]==ep['text'],'addition literal '+role)
        for a in c['corrected_or_retained_source_alternatives']:
            packet,v=views[a['passage_id']];item=next(x for x in v['native_context']['items'] if x['self_ref']==a['native_pointer'])
            check(sha(a['packet']['path'])==a['packet']['sha256'],'corrected source packet hash')
            check(v['passage']['text'][a['start']:a['end']]==a['text'],'corrected exact source quote')
            check(item['text'][a['native_start']:a['native_end']]==a['text'],'corrected native pointer and local offsets')
            check(item.get('orig')==a['original_native_field'] and item['text']==a['projected_native_field'],'native original/converted context unchanged')
            check(packet['parent_pdf_sha256']==a['native']['source_work_sha256'] and packet['source_pdf_sha256']==a['native']['excerpt_pdf_sha256'],'corrected original source-work/excerpt identity')
    for report in inv['reports']:
        entry=detail(report['raw']['path'])['reports'][report['report_index']]
        raw=entry['report']['raw_json']
        check(hashlib.sha256(raw.encode()).hexdigest()==report['raw_json_sha256'],'raw provider report exact digest')
        check(entry['diagnostics']==report['diagnostics'] and entry['association_diagnostics']==report['association_diagnostics'],'provider unresolved/content diagnostics retained')
        try:json.loads(raw);state='parsed'
        except (ValueError,TypeError):state='failed'
        check(state==report['parse_state'],'raw syntax separately assessed')
    check(len(data['source64_cases'])==64 and all(not c['whole_case_capture'] for c in data['source64_cases']),'all64 source cases retained without full capture promotion')
    check(inv['task_counts']=={'extract.m1_annotations':48,'extract.m1_candidates':48,'structure.definition_components':1},'97 task family membership')
    failures=[c for c in checks if not c['passed']]
    files=['model161-assessment.json','model161-provider-inventory.json','model161-input-pins.json','build_model_assessment.py','validate_model.py','README.md']
    receipt={'protocol':'gs120-final-model-C-literal-validation-1','timestamp_utc':datetime.now(timezone.utc).isoformat(),
        'outcome':'failed' if failures else 'passed','command':'uv run python docs/design_review/evidence/2026-11-06_wce-gs120/assessment/final-source-capture/validate_model.py',
        'check_count':len(checks),'failures':failures,'model_components':44,'additions':9,'raw_envelopes':97,
        'artifact_hashes':{f:sha(PREFIX+f) for f in files},
        'limits':'Literal/hash/native/source/capture transcription only; not a semantic truth oracle, probability calibration, public authority or whole-corpus efficacy.'}
    (HERE/'model161-validation-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='artifact_hashes'}))
    return int(bool(failures))


if __name__=='__main__':raise SystemExit(main())
