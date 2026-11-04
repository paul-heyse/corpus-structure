from pathlib import Path
import json
from sqlalchemy import select, text
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.identity import canonical_bytes

folder=Path(__file__).parent/'attempt-001'
with open_runtime_engine(Settings(),'m1-recovery-failure-inventory',purpose='read') as engine:
 with engine.connect() as conn:
  r,t,c,m=map(table,('ops.run','ops.task','ops.method_config','ops.method'))
  rows=[]
  for rid in (17,18):
   run=dict(conn.execute(select(r).where(r.c.id==rid)).mappings().one())
   taskrows=[dict(x) for x in conn.execute(select(t,m.c.name.label('method')).join(c,t.c.method_config_id==c.c.id).join(m,c.c.method_id==m.c.id).where(t.c.run_id==rid).order_by(t.c.id)).mappings()]
   rows.append(dict(run=run,tasks=taskrows))
  catalogs=[dict(x) for x in conn.execute(text("SELECT table_schema,table_name,column_name FROM information_schema.columns WHERE table_schema='ops' AND (table_name LIKE '%source_view%' OR table_name LIKE '%cut%') ORDER BY table_name,ordinal_position")).mappings()]
  data=dict(outcome='failed',question='new-run recovery after actual cancellation',runs=rows,catalogs=catalogs,at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())
  (folder/'recovery-failure.json').write_bytes(canonical_bytes(json.loads(json.dumps(data,default=str))))
  print(json.dumps(data,default=str))
