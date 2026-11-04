"""Read archived exact release; validate independent bytes without reference/prediction reads."""
import json,pathlib,traceback
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.records import authenticated_source_record_coordinates
from corpus_structure.evaluate.record_references import decode_frame,decode_authored
ROOT=pathlib.Path(__file__).resolve().parent;F=ROOT.parent/'freeze-002'
manifest=json.loads((F/'manifest.json').read_text());results=[]
with open_runtime_engine(Settings(),'m1-reference-author-A-validation',purpose='read') as engine, engine.connect() as conn:
 prepared=open_release(conn,manifest['release_id'])
 for group in manifest['sets']:
  for unit in group['units']:
   p=ROOT/unit['path'];packet=json.loads((F/group['directory']/unit['path']).read_bytes());frame=decode_frame(packet['source_frame']);authored=p.read_bytes();payload=json.loads(authored)
   try:
    coords=authenticated_source_record_coordinates(conn,prepared,run_id=group['source_run_id'],source_view_id=frame.pin['source_view_id'],source=frame.pin['source'],records=tuple(prepared.validate_json('SourceRecord',json.dumps(r)).model_dump(mode='python') for r in payload['records']))
    result=decode_authored(prepared,authored,frame,coordinate_texts=coords)
    row=dict(unit=unit['unit_id'],outcome='passed',records=len(result['records']))
   except Exception as e:
    row=dict(unit=unit['unit_id'],outcome='failed',error=repr(e),traceback=traceback.format_exc())
   results.append(row);print(json.dumps(row),flush=True)
print(json.dumps(dict(outcome='passed' if all(r['outcome']=='passed' for r in results) else 'failed',units=results),indent=2))
