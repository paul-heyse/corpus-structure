"""Read immutable fresh operation custody and protected review exports."""
from pathlib import Path
from hashlib import sha256
import argparse,json,sys
sys.dont_write_bytecode=True
from sqlalchemy import select
from corpus_structure.evaluate import operation_assessment as assessment
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_run
from corpus_structure.semantic.runtime_bindings import runtime_fingerprint
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from pce03_native_assessment_001 import RAW,PROJECT,read,write,digest

p=argparse.ArgumentParser(__doc__);p.add_argument('--receipt',required=True);p.add_argument('--source-grade');p.add_argument('--output-grade');args=p.parse_args()
target=RAW/f'{args.receipt}.json'
if target.exists():raise FileExistsError(target)
(RAW/f'{args.receipt}-script.py').write_bytes(Path(__file__).read_bytes())
registrations=[read('pce03-fresh-source-register-003.json'),read('pce03-fresh-output-register-003.json')]
reports=[];run_receipts=[]
with open_runtime_engine(Settings(),'pce03-final-custody',purpose='evaluate') as engine,engine.begin() as conn:
    units,passes,frames,runs,completed=map(table,('eval.reference_unit','eval.reference_pass','eval.reference_frame','ops.run','ops.completed_result'))
    for run_id in (27,28):
        row=dict(conn.execute(select(runs).where(runs.c.id==run_id)).mappings().one())
        assert row['sealed'] and row['status']=='finished'
        prepared=open_release(conn,row['release_id']);runtime=runtime_binding_for_run(conn,run_id,prepared)
        assert runtime.runtime_id==row['runtime_id']
        run_receipts.append(dict(run_id=run_id,release_id=row['release_id'],runtime_id=row['runtime_id'],sealed=True,status=row['status'],
            source_fingerprint=runtime_fingerprint(digests=runtime.implementation_digests),runtime_manifest_sha256=sha256(runtime.manifest).hexdigest(),
            runtime_archive_sha256=sha256(runtime.archive).hexdigest(),completed_cut_id=conn.scalar(select(completed.c.cut_id).where(completed.c.run_id==run_id))))
    for registration in registrations:
        for question,entry in registration['sets'].items():
            set_id=entry['set_id'];export=assessment.review_export(conn,project_id=PROJECT,set_id=set_id)
            assert export['partition']=='feature_fit' and not export['judgments_exposed'] and export['judgments']==[]
            captured=[]
            selected=conn.execute(select(passes).join(units,units.c.id==passes.c.unit_id).where(units.c.set_id==set_id).order_by(passes.c.id)).mappings().all()
            assert {row['id'] for row in selected}==set(entry['pass_ids'].values())
            for row in selected:
                assert sha256(bytes(row['authored'])).hexdigest()==row['content_digest']
                payload=json.loads(bytes(row['authored']))
                owned_frame=conn.execute(select(frames.c.source_frame).where(frames.c.pass_id==row['id'])).scalar_one()
                frame=assessment.decode_frame(owned_frame)
                decoded=assessment.decode_authored(bytes(row['authored']),frame)
                if row['pass_kind']=='C':
                    expected={other['id'] for other in selected if other['unit_id']==row['unit_id'] and other['pass_kind'] in ('A','B')}
                    assert set(payload['adjudication_passes'])==expected
                    assert len({other['actor'] for other in selected if other['unit_id']==row['unit_id']})==3
                captured.append(dict(pass_id=row['id'],unit_id=row['unit_id'],kind=row['pass_kind'],actor=row['actor'],
                    content_digest=row['content_digest'],frame_digest=sha256(canonical_bytes(owned_frame)).hexdigest(),
                    case_count=len(payload['cases']),source_artifact_sha256s=sorted({case['assessor_provenance']['source_artifact_sha256'] for case in payload['cases']})))
            reports.append(dict(question=question,set_id=set_id,passes=captured,protected_review_export=export))
    stored=[]
    for name in (args.source_grade,args.output_grade):
        if not name:continue
        artifact=read(name)
        for question,entry in artifact['grades'].items():
            values=[entry['baseline'],entry['revised']] if 'baseline' in entry else [entry]
            for value in values:
                actual=assessment.read_evaluation(conn,project_id=PROJECT,evaluation_id=value['id'])
                assert actual==value['result']
                stored.append(dict(evaluation_id=value['id'],set_id=value['set_id'],run_id=value['run_id'],result_sha256=sha256(canonical_bytes(actual)).hexdigest()))
    project=table('data.project')
    defaults=dict(conn.execute(select(project).where(project.c.project_id==PROJECT)).mappings().one())
    assert defaults['active_release_id'] is None and defaults['selected_result_run_id'] is None and defaults['generation']==0
write(target,dict(outcome='passed',runs=run_receipts,reference_sets=reports,stored_evaluations=stored,project_defaults=defaults,
    scope='Fresh finite feature-fit source/output operations; protected exports withhold judgments; no population/model-quality/publication or portable-complete claim',
    script_sha256=digest(Path(__file__))))
print(json.dumps(dict(outcome='passed',receipt=str(target))))
