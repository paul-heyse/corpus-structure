"""Verify the actual checkpoint files and retained completed-task architecture."""
import json
from hashlib import sha256
from pathlib import Path
from sqlalchemy import text
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.observations import source_python
from corpus_structure.settings import Settings
HERE=Path(__file__).resolve().parent
configuration=json.loads((HERE/'baseline003/gs120-all120-pages/configuration.json').read_bytes())
profile=configuration['m1']
assert profile['checkpoint']=='fastino/gliner2.5-base-v1'
assert configuration['definition']['profile']['checkpoint']==profile['checkpoint']
verified={}
for name,digest in profile['artifact_hashes']:
    actual=sha256((Path(profile['snapshot'])/name).read_bytes()).hexdigest()
    assert actual==digest
    verified[name]=actual
with open_runtime_engine(Settings(),'verify-actual-gliner25',purpose='read') as engine,read_snapshot(engine) as conn:
    row=conn.execute(text("SELECT t.id,r.body FROM ops.task t JOIN ops.task_result r ON r.task_id=t.id JOIN ops.method_config c ON c.id=t.method_config_id JOIN ops.method m ON m.id=c.method_id WHERE t.run_id=139 AND m.name='extract.m1_candidates' ORDER BY t.id LIMIT 1")).one()
    profiles=source_python(row.body['parse_detail'])['effective_profiles']
    actual=[json.loads(value) for value in profiles.values()]
    assert actual and all(value['config']['architecture']=='boundary' and value['snapshot']==profile['snapshot'] for value in actual)
    result=dict(outcome='passed',verified_date='2026-11-06',run_id=139,task_id=row.id,checkpoint=profile['checkpoint'],revision=profile['revision'],architecture='boundary',loader='AutoExtractor.from_pretrained',artifact_hashes=verified,effective_profile_ids=list(profiles),scope='Pinned files plus actual retained effective runtime profile; extraction quality assessed separately')
(HERE/'gliner25-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='artifact_hashes'}))
