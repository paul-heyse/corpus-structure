"""Read-only verification of pinned GLiNER2.5 files and an actual completed current task."""
import argparse
import json
from hashlib import sha256
from pathlib import Path
from sqlalchemy import text
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.observations import source_python
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--run',type=int,required=True);p.add_argument('--configuration',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
configuration=json.loads(args.configuration.read_bytes());profile=configuration['m1']
assert profile['checkpoint']=='fastino/gliner2.5-base-v1'
assert profile['revision']=='54785d51df8d86a0d8f2eb212fec15871aad2c4d'
assert configuration['definition']['profile']['checkpoint']==profile['checkpoint']
verified={}
for name,digest in profile['artifact_hashes']:
 actual=sha256((Path(profile['snapshot'])/name).read_bytes()).hexdigest()
 assert actual==digest;verified[name]=actual
with open_runtime_engine(Settings(),'verify-current-actual-gliner25',purpose='read') as engine,read_snapshot(engine) as conn:
 row=conn.execute(text("SELECT t.id,r.body FROM ops.task t JOIN ops.task_result r ON r.task_id=t.id JOIN ops.method_config c ON c.id=t.method_config_id JOIN ops.method m ON m.id=c.method_id WHERE t.run_id=:run AND m.name='extract.m1_candidates' ORDER BY t.id LIMIT 1"),dict(run=args.run)).one()
 profiles=source_python(row.body['parse_detail'])['effective_profiles'];actual=[json.loads(value) for value in profiles.values()]
 assert actual and all(value['config']['architecture']=='boundary' and value['snapshot']==profile['snapshot'] and value['dtype']=='float32' and value['device']=='cpu' for value in actual)
 result=dict(outcome='passed',verified_date='2026-11-06',run_id=args.run,task_id=row.id,checkpoint=profile['checkpoint'],revision=profile['revision'],architecture='boundary',loader='AutoExtractor.from_pretrained',artifact_hashes=verified,effective_profile_ids=list(profiles),effective_device='cpu',effective_dtype='float32',configuration_sha256=sha256(args.configuration.read_bytes()).hexdigest(),scope='Pinned files and actual retained completed-task runtime profile; enclosing run completion and extraction quality assessed separately')
with args.out.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='artifact_hashes'}))
