"""Explicit structural-reference import bundle preflight/apply; no label synthesis.

Preflight has no database access. Apply must only be invoked after root GO and
supplied authenticated final run/cut/task/product pins. No publication is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path

from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference, StructuralEvaluationFrame,
    create_structural_reference_set, record_structural_reference_pass,
    score_structural_reference,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralProductReport


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def read_checked(base,reference):
    path=(base/reference['path']).resolve()
    if sha(path)!=reference['sha256']:raise ValueError('frozen file hash changed: '+str(path))
    return path,path.read_bytes()


def questions(case):
    return (case.component_id,case.facet,case.path)


def preflight(bundle_path):
    bundle=json.loads(bundle_path.read_text());base=bundle_path.parent
    if bundle['protocol']!='wce-protected-structural-import-1':raise ValueError('unsupported explicit bundle')
    if bundle.get('publication_requested') is not False:raise ValueError('this importer never grants or executes publication')
    ip,ib=read_checked(base,bundle['inspection']);inspection=json.loads(ib)
    if (inspection['run_id'],inspection['cut_id'],inspection['release_id'])!=(bundle['candidate_run_id'],bundle['candidate_cut_id'],bundle['release_id']):raise ValueError('candidate run/cut/release differs from authenticated bundle')
    if bundle['selected_task_id'] not in inspection['task_ids']:raise ValueError('candidate selected task outside frozen inspection')
    if len(inspection['reports'])!=1:raise ValueError('select one exact structural report')
    product=StructuralProductReport.model_validate(inspection['reports'][0])
    if product.product_id!=bundle['product_id']:raise ValueError('candidate product identity differs')
    if {s.project_id for s in product.inputs.sources}!={bundle['project_id']}:raise ValueError('source project differs')
    frozen=[]
    for f in bundle.get('additional_frozen_inputs',[]):read_checked(base,f)
    for selected in bundle['sets']:
        fp,fb=read_checked(base,selected['frame']);frame=StructuralEvaluationFrame.model_validate_json(fb)
        if frame.identity!=selected['frame_digest']:raise ValueError('frozen frame digest differs')
        if frame.partition not in {'development','feature_fit'} or not frame.exposure_history:raise ValueError('exposed development imports require exposure history and nonheldout partition')
        if frame.inputs!=product.inputs or frame.operation!=product.kind:raise ValueError('frame sources/operation differ from exact product')
        if frame.direction=='output_first' and frame.product_ids!=(product.product_id,):raise ValueError('output-first frame must freeze this exact product only')
        passes=[];bykind={};actors=set()
        for entry in selected['passes']:
            kind=entry['pass_kind'];actor=entry['actor']
            if kind not in {'A','B','C'} or kind in bykind or not actor or actor in actors:raise ValueError('passes require unique slots and actual distinct actors')
            if kind=='C' and entry['authoring_kind']!='adjudication':raise ValueError('C slot requires actual adjudication, not a third unrelated inventory')
            if kind!='C' and entry['authoring_kind']!='independent':raise ValueError('A/B slots require independent authored case bytes')
            ap,ab=read_checked(base,entry['authored']);ref=StructuralAuthoredReference.model_validate_json(ab)
            if ref.frame_digest!=frame.identity:raise ValueError('authored bytes differ from frozen frame')
            pp,pb=read_checked(base,entry['provenance']);provenance=json.loads(pb)
            # This external sidecar preserves who authored each literal; no actual-to-expected adapter.
            if provenance['actor']!=actor or provenance['pass_kind']!=kind:raise ValueError('author provenance differs from pass actor/slot')
            origins=provenance['case_origins']
            if set(origins)!={c.case_id for c in ref.cases}:raise ValueError('every exact machine case requires explicit independent expectation origin')
            for case in ref.cases:
                origin=origins[case.case_id]
                if not origin.get('source_artifact') or not origin.get('source_sha256') or not origin.get('source_pointer') or not origin.get('mapping_decision'):raise ValueError('case lacks source authoring and exact mapping rationale')
                read_checked(base,{'path':origin['source_artifact'],'sha256':origin['source_sha256']})
                if origin.get('copied_actual_as_expected') is not False:raise ValueError('expected values cannot be declared copied actual')
                if case.judgment=='supported' and case.expected is None:raise ValueError('supported literal reference needs a real independent expected value')
            comparison=score_structural_reference(frame,ref,product.model_dump(mode='json',exclude_none=True))
            entry_data=dict(entry,authored_bytes=ab,reference=ref,comparison=comparison)
            passes.append(entry_data);bykind[kind]=entry_data;actors.add(actor)
        if 'C' in bykind:
            if not {'A','B'}<=bykind.keys():raise ValueError('no C adjudication without independently authored A/B')
            mapping=selected.get('adjudication_case_correspondence',{})
            if set(mapping)!={c.case_id for c in bykind['C']['reference'].cases}:raise ValueError('each C case requires explicit A/B question correspondence')
            ac={c.case_id:c for c in bykind['A']['reference'].cases};bc={c.case_id:c for c in bykind['B']['reference'].cases}
            for c in bykind['C']['reference'].cases:
                link=mapping[c.case_id]
                if link['A'] not in ac or link['B'] not in bc:raise ValueError('C correspondence references unauthored case')
                if questions(c)!=questions(ac[link['A']]) or questions(c)!=questions(bc[link['B']]):raise ValueError('differently authored questions cannot become three votes')
        frozen.append(dict(selected=selected,frame=frame,passes=passes))
    if not frozen:raise ValueError('no exact representable structural sets supplied')
    return bundle,product,frozen


def apply(bundle,product,sets):
    # Called only after explicit --apply and coordinator GO. One transaction; no publication API.
    from sqlalchemy import text
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.settings import Settings
    from corpus_structure.evaluate.record_references import assign_origin
    receipts=[]
    with open_runtime_engine(Settings(),application_name='wce-protected-current',purpose='evaluate') as engine,engine.begin() as conn:
        row=conn.execute(text('''SELECT r.project_id,r.release_id,c.final,t.status,
               t.id selected_task_id,COALESCE(t.reused_task_id,t.id) origin_task_id,result.body
            FROM ops.run r JOIN ops.input_cut c ON c.run_id=r.id
            JOIN ops.cut_task m ON m.cut_id=c.id JOIN ops.task t ON t.id=m.task_id
            JOIN ops.task_result result ON result.task_id=COALESCE(t.reused_task_id,t.id)
            WHERE r.id=:run AND c.id=:cut AND t.id=:task'''),
            {'run':bundle['candidate_run_id'],'cut':bundle['candidate_cut_id'],'task':bundle['selected_task_id']}).mappings().one()
        if row['project_id']!=bundle['project_id'] or row['release_id']!=bundle['release_id'] or not row['final'] or row['status'] not in {'done','reused'}:raise ValueError('native completed candidate custody differs from final pins')
        retained=StructuralProductReport.model_validate(row['body']['structural_product'])
        if retained!=product:raise ValueError('native retained candidate body differs from complete frozen product')
        for data in sets:
            selected=data['selected'];frame=data['frame']
            origin=selected.get('assign_origin')
            if origin:
                if origin['origin_group']!='grinstead-snell' or origin['partition']!=frame.partition:raise ValueError('origin group/partition differs from approved scope')
                assign_origin(conn,project_id=bundle['project_id'],origin_group=origin['origin_group'],partition=origin['partition'],source_uris=tuple(origin['source_uris']),provenance=origin['provenance'])
            sid=create_structural_reference_set(conn,project_id=bundle['project_id'],release_id=bundle['release_id'],frame=frame)
            ids={};passes=[]
            for entry in sorted(data['passes'],key=lambda e:'ABC'.index(e['pass_kind'])):
                kind=entry['pass_kind'];parents=(ids['A'],ids['B']) if kind=='C' else ()
                pid=record_structural_reference_pass(conn,set_id=sid,pass_kind=kind,actor=entry['actor'],authored=entry['authored_bytes'],parents=parents)
                ids[kind]=pid;passes.append({'pass_kind':kind,'actor':entry['actor'],'pass_id':pid,'authored_sha256':hashlib.sha256(entry['authored_bytes']).hexdigest(),'parents':list(parents)})
            receipts.append({'set_id':sid,'frame_digest':frame.identity,'passes':passes,'scope':'protected custody only; no publication or whole-report correctness'})
    return receipts


def main():
    p=argparse.ArgumentParser();p.add_argument('bundle',type=Path);p.add_argument('--apply',action='store_true',help='Only after explicit coordinator GO; writes protected eval custody, never publishes.');args=p.parse_args()
    bundle,product,sets=preflight(args.bundle)
    if args.apply and bundle.get('native_import_authorized') is not True:
        raise ValueError('root GO and an authenticated final import bundle are required before native writes')
    receipt={'protocol':'wce-protected-current-import-receipt-1','bundle_sha256':sha(args.bundle),'candidate_product_id':product.product_id,'outcome':'passed','mode':'native_apply' if args.apply else 'offline_preflight','database_writes':'performed' if args.apply else 'not_run','publication':'not_requested','sets':[{'frame_digest':d['frame'].identity,'passes':[{'pass_kind':e['pass_kind'],'actor':e['actor'],'case_count':len(e['reference'].cases),'comparison':e['comparison']} for e in d['passes']]} for d in sets]}
    if args.apply:receipt['native_receipts']=apply(bundle,product,sets)
    print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
