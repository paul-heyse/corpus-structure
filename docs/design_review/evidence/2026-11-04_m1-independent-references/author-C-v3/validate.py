"""Read-only authentication and archived-release decoding of exact C author bytes."""
import hashlib,json,pathlib,traceback,datetime,sys
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.records import authenticated_source_record_coordinates
from corpus_structure.evaluate.record_references import decode_frame,decode_authored
ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=pathlib.Path(__file__).resolve().parent
release='release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd'
results=[]
with open_runtime_engine(Settings(),'m1-C-validation',purpose='read') as engine:
 with engine.connect() as conn:
  prepared=open_release(conn,release)
  for i in range(1,12):
   p=OUT/f'rawunit-{i}.json';b=p.read_bytes();payload=json.loads(b);packet=json.loads((ROOT/f'adjudication-inputs-002/unit-{i}.json').read_text());frame=decode_frame(packet['source']['source_frame'])
   run=11 if i<=2 else 12 if i<=9 else 13
   result={'unit_id':i,'path':p.name,'sha256':hashlib.sha256(b).hexdigest(),'run_id':run,'adjudication_passes':packet['adjudication_passes'],'read_only':True}
   try:
    assert payload['adjudication_passes']==packet['adjudication_passes']
    typed=prepared.validate_json('ReferenceRecordBatch',b).model_dump(mode='python')
    coords=authenticated_source_record_coordinates(conn,prepared,run_id=run,source_view_id=frame.pin['source_view_id'],source=frame.pin['source'],records=tuple(typed['records']))
    got=decode_authored(prepared,b,frame,coordinate_texts=coords)
    result.update(outcome='passed',accepted_records=len(got['records']),authenticated_coordinates=len(coords))
   except Exception as e:
    result.update(outcome='failed',error_type=type(e).__name__,error=str(e),traceback=traceback.format_exc());conn.rollback()
   results.append(result);print(json.dumps(result),flush=True)
report={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actor':'gpt-6.1-sol-high-C-v3','canonical_session':'/root/m1_reference_c_v3','release_id':release,'outcome':'passed'if all(x['outcome']=='passed'for x in results)else 'failed','native_read_only_validation':True,'prediction_read':'not_run','registration':'not_run (root owns protected registration)','units':results}
path=OUT/sys.argv[1] if len(sys.argv)>1 else OUT/'validation.json';path.write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(0 if report['outcome']=='passed'else 1)
