"""Read-only final evidence consistency check; no scientific or whole-report claim."""
import datetime
import hashlib
import json
from pathlib import Path
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.evaluate.structural_assessment import StructuralAuthoredReference,StructuralEvaluationFrame
from corpus_structure.semantic.structural_products import StructuralProductReport

P=Path(__file__).resolve().parent
GS=P.parents[2]

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jsonl(name):return [json.loads(r['payload_json']) for r in (json.loads(l) for l in (P/'review-bundle'/name).read_text().splitlines())]

def main():
    checks=[]
    def check(value,label):
        checks.append({'check':label,'passed':bool(value)})
    custody=read(P/'input-custody.json')
    for f in custody['files']:check(sha(Path(f['path']))==f['sha256'],'frozen custody '+f['path'])
    native=read(P/'protected-reference-receipt.json');frame=StructuralEvaluationFrame.model_validate(read(P/'frame.final160.json'))
    refs={k:StructuralAuthoredReference.model_validate_json((P/(k+'.authored.rebound.json')).read_bytes()) for k in 'ABC'}
    for k,ref in refs.items():
        original=read(P/'original'/(k+'.authored.original.json'));current=read(P/(k+'.authored.rebound.json'))
        check({key:value for key,value in original.items() if key!='frame_digest'}=={key:value for key,value in current.items() if key!='frame_digest'},'only frame_digest rebound '+k)
        check(ref.frame_digest==frame.identity,'exact common frame '+k)
    check(native['C_exact_parent_ids']==[native['pass_ids']['A'],native['pass_ids']['B']],'C exact native parents')
    check(sha(P/'C.authored.rebound.json')==native['c_content_digest'],'C retained byte digest')
    check(read(P/'C-parent-binding-committed.json')['native_C_pass_id']==native['pass_ids']['C'],'committed C binding sidecar')
    comparisons={k:read(P/(k+'.comparison.json')) for k in 'ABC'}
    check(all(row['outcome']=='match' for c in comparisons.values() for row in c['cases'] if row['judgment']=='supported'),'all independent positive literal matches')
    controls=read(P/'native-refusal-controls.json')['controls'];counts=read(P/'public-assertion-counts.json')['selected_task_counts']
    for c in controls:
        check(c['outcome']=='refused' and c['sqlstate']=='23514' and 'structural public witness cannot resolve exact current custody' in c['reason'],'native intended refusal '+c['control'])
        check(counts[str(c['selected_task'])]==0,'zero public assertions for refused '+c['control'])
    result=read(P/'publication-result.json');check(result['publication_run']==169 and result['publication_cut']==225 and result['origin_task']==800 and result['producer_reexecuted'] is False,'exact positive publication custody')
    check(counts[str(result['selected_task'])]==2,'two positive public assertions')
    expected={canonical_bytes(c.expected) for c in refs['C'].cases if c.facet=='public_statement' and c.judgment=='supported'}
    actual=jsonl('structural_public_assertions.jsonl')
    check(len(actual)==2 and {canonical_bytes(a['statement']) for a in actual}==expected,'export exact independently supported statements')
    check(all(a['cut_id']==225 and a['selected_task_id']==956 and a['origin_task_id']==800 and a['c_pass_id']==45 and a['set_id']==13 for a in actual),'export exact assertion custody')
    products=jsonl('structural_products.jsonl');report=StructuralProductReport.model_validate(products[0]['report'])
    check(len(products)==1 and report.standing=='private_proposal' and len(report.definition_components.components)==35,'private report and all35 retained')
    check({s['source_view_id'] for s in jsonl('sources.jsonl')}=={s.source_view_id for s in report.inputs.sources},'all48 original source views exported')
    manifest=read(P/'export-verification.json')
    check(manifest['completeness']=='selected_source_closure' and manifest['original_source_completeness']=='not_established' and manifest['scientific_truth']=='not_established','file closure and truth limits preserved')
    check(manifest['relations']['documents']['rows']==12 and manifest['relations']['source_producers']['rows']==12,'twelve physical source documents/producers')
    predecessor=read(P/'published-predecessor-references.json')
    check(predecessor['run_id']==169 and predecessor['cut_id']==225 and len(predecessor['component_references'])==2,'actual native resolved predecessor references retained')
    failures=[c for c in checks if not c['passed']]
    print(json.dumps({'outcome':'failed' if failures else 'passed','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':'uv run python docs/design_review/evidence/2026-11-06_wce-gs120/assessment/protected-current/native160/verify_native160.py','checks':len(checks),'failures':failures,'publication_run':169,'publication_cut':225,'public_assertions':2,'source_views':48,'source_documents':12,'protected_set':13,'protected_passes':native['pass_ids'],'refusal_controls':len(controls),'database_writes':'not_run','scope':'Two exact supported source-attributed attachments and their custody/reader/file closure only. No scientific truth, complete scope, full report correctness, held-out result, or general calibration.'},ensure_ascii=False,indent=2))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
