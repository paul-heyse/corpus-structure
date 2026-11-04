"""Read-only settlement and reuse-custody checks for owned runs 17 and 18."""
from pathlib import Path
from datetime import datetime, timezone
import json
from hashlib import sha256
from sqlalchemy import select, func, text
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.identity import canonical_bytes

folder=Path(__file__).parent/'attempt-001'
with open_runtime_engine(Settings(),'m1-recovery-final-settlement',purpose='read') as engine:
 with engine.connect() as conn:
  t,r,v,s=map(table,('ops.task','ops.run','kb.source_view','ops.run_source_view'))
  own_tasks=[dict(x) for x in conn.execute(select(t.c.id,t.c.status,t.c.run_id,t.c.reused_task_id,t.c.result_digest).where(t.c.run_id.in_([17,18]))).mappings()]
  counts={name:conn.execute(select(func.count()).select_from(table(name)).where(table(name).c.task_id==71)).scalar_one() for name in ('ops.task_result','kb.observation')}
  pin=dict(conn.execute(select(v.c.id,v.c.native_task_id,v.c.native_content_digest,v.c.section_pointer).where(v.c.id==22)).mappings().one())
  definitions={name:conn.execute(text('SELECT pg_get_functiondef(CAST(:name AS regprocedure))'),dict(name=name)).scalar_one() for name in ('ops.select_reused_source_views(bigint,bigint)','ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb)')}
  hashes={name:sha256(body.encode()).hexdigest() for name,body in definitions.items()}
  data=dict(at=datetime.now(timezone.utc).isoformat(),tasks=own_tasks,cancelled_task71_rows=counts,native_view22=pin,function_sha256=hashes,child_pid3644845_absent=not Path('/proc/3644845').exists(),parent_pid3643773_absent=not Path('/proc/3643773').exists(),open_owned_tasks=[x['id'] for x in own_tasks if x['status'] in ('pending','running','awaiting_agent')])
  assert not data['open_owned_tasks'] and all(n==0 for n in counts.values()) and data['child_pid3644845_absent']
  (folder/'settlement-verification.json').write_bytes(canonical_bytes(data))
  (folder/'live-owned-function-definitions.json').write_bytes(canonical_bytes(definitions))
  print(json.dumps(dict(outcome='passed',**data)))
