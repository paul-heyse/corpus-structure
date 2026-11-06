"""Exact authored OperationFrameV2 bundle preflight/apply; no inventory-to-gold inference.

Input is an explicitly authored literal native operation bundle, never raw prose inventories.
Unrelated C-only inventories remain single independent passes with original-author provenance;
they cannot receive a C adjudication slot or invented A/B votes.
"""
import argparse
import hashlib
import json
from pathlib import Path

from corpus_structure.evaluate.operation_assessment import (
    OperationEvaluationFrameV2, decode_frame, decode_authored, score_cases,
    create_reference_set, record_pass,
)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def checked(base,f):
    p=(base/f['path']).resolve()
    if sha(p)!=f['sha256']:raise ValueError('frozen operation file changed: '+str(p))
    return p.read_bytes()


def preflight(path):
    b=json.loads(path.read_text());base=path.parent
    if b['protocol']!='wce-protected-operation-import-1' or b.get('publication_requested') is not False:raise ValueError('unsupported operation import scope')
    frames={k:decode_frame(json.loads(checked(base,v))) for k,v in b['frames'].items()}
    if not frames or any(not isinstance(f,OperationEvaluationFrameV2) for f in frames.values()):raise ValueError('explicit opportunity-bearing V2 frames required')
    for key,f in frames.items():
        if f.unit!=key or f.release_id!=b['release_id'] or f.partition!=b['partition'] or f.partition not in {'development','feature_fit'} or not f.exposure_history:raise ValueError('operation unit/release/exposed partition mismatch')
    contributions=json.loads(checked(base,b['contributions']))
    closure=json.loads(checked(base,b['endpoint_closure'])) if b.get('endpoint_closure') else []
    # Contributions stay literal. No contextual.relationship -> relation.defined_by rewriting.
    units=[]
    for key,f in frames.items():
        entries=b['passes'][key];seen={};actors=set();validated=[]
        for entry in entries:
            kind=entry['pass_kind'];actor=entry['actor']
            if kind not in {'A','B','C'} or kind in seen or actor in actors:raise ValueError('distinct actual authors and pass slots required')
            if kind=='C' and entry['authoring_kind']!='adjudication':raise ValueError('unrelated C inventory cannot be adjudication')
            if kind!='C' and entry['authoring_kind']!='independent':raise ValueError('first/second pass must be independent actual authoring')
            authored=checked(base,entry['authored']);payload=decode_authored(authored,f)
            provenance=json.loads(checked(base,entry['provenance']))
            if provenance['actor']!=actor or provenance['pass_kind']!=kind:raise ValueError('operation provenance identity mismatch')
            if set(provenance['case_origins'])!={c.case_id for c in payload['cases']}:raise ValueError('every typed alternative needs exact authoring origin')
            for c in payload['cases']:
                origin=provenance['case_origins'][c.case_id]
                checked(base,{'path':origin['source_artifact'],'sha256':origin['source_sha256']})
                if not origin.get('source_pointer') or not origin.get('mapping_decision') or origin.get('copied_actual_as_expected') is not False:raise ValueError('no invented or copied-actual alternatives')
            comparison=score_cases(f,payload['cases'],contributions,endpoint_closure=closure)
            seen[kind]=payload;actors.add(actor);validated.append(dict(entry,authored_bytes=authored,payload=payload,comparison=comparison))
        if 'C' in seen:
            if not {'A','B'}<=seen.keys():raise ValueError('no adjudication without actual independent A/B')
            corr=b['adjudication_case_correspondence'][key]
            if set(corr)!={c.case_id for c in seen['C']['cases']}:raise ValueError('each adjudication question needs explicit parents')
            aa={c.case_id:c for c in seen['A']['cases']};bb={c.case_id:c for c in seen['B']['cases']}
            for c in seen['C']['cases']:
                parent=corr[c.case_id]
                for author,lookup in [('A',aa),('B',bb)]:
                    if parent[author] not in lookup:raise ValueError('unrelated source selection is not a vote')
                    other=lookup[parent[author]]
                    if (c.facet,c.contribution_id,c.anchor_ids)!=(other.facet,other.contribution_id,other.anchor_ids):raise ValueError('adjudication source/operation question differs')
        units.append({'key':key,'frame':f,'passes':validated})
    return b,frames,units


def apply(b,frames,units):
    from sqlalchemy import select
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.settings import Settings
    from corpus_structure.semantic.metadata import table
    receipts=[]
    with open_runtime_engine(Settings(),application_name='wce-protected-source-operations',purpose='evaluate') as engine,engine.begin() as conn:
        created=create_reference_set(conn,project_id=b['project_id'],source_run_id=b['source_run_id'],source_cut_id=b['source_cut_id'],label=b['label'],legacy_split='dev',guideline=b['guideline'],guideline_text=b['guideline_text'],partition=b['partition'],sampling=b['sampling'],frames=frames)
        native_units=table('eval.reference_unit')
        for u in units:
            unit_id=conn.scalar(select(native_units.c.id).where(native_units.c.set_id==created['set_id'],native_units.c.unit_key==u['key']))
            passes=[]
            for e in sorted(u['passes'],key=lambda x:'ABC'.index(x['pass_kind'])):
                # C authored bytes must already contain exact native A/B pass IDs. Never patch author bytes here.
                pid=record_pass(conn,unit_id=unit_id,pass_kind=e['pass_kind'],actor=e['actor'],authored=e['authored_bytes'],frame=u['frame'])
                passes.append({'id':pid,'kind':e['pass_kind'],'actor':e['actor'],'authored_sha256':hashlib.sha256(e['authored_bytes']).hexdigest()})
            receipts.append({'unit_id':unit_id,'unit_key':u['key'],'passes':passes})
    return {'set_id':created['set_id'],'units':receipts}


def main():
    p=argparse.ArgumentParser();p.add_argument('bundle',type=Path);p.add_argument('--apply',action='store_true',help='Only after root GO and authenticated exact pins.');args=p.parse_args()
    b,frames,units=preflight(args.bundle)
    if args.apply and b.get('native_import_authorized') is not True:
        raise ValueError('root GO and an authenticated final operation bundle are required before native writes')
    if args.apply and any(e['pass_kind']=='C' for u in units for e in u['passes']):raise ValueError('Operation C bytes need actual stored A/B IDs; import A/B first, then separately freeze C against those native parents. This tool refuses to synthesize or patch C bytes.')
    result={'outcome':'passed','mode':'native_apply' if args.apply else 'offline_preflight','database_writes':'performed' if args.apply else 'not_run','publication':'not_requested','bundle_sha256':sha(args.bundle),'units':[{'key':u['key'],'passes':[{'kind':e['pass_kind'],'actor':e['actor'],'comparison':e['comparison']} for e in u['passes']]} for u in units]}
    if args.apply:result['native_receipts']=apply(b,frames,units)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
