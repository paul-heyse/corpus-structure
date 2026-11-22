from datetime import datetime
from collections import defaultdict
from pathlib import Path
import json,re
receipt='f02c6b33e0d14cd4b77b97c5a3394854'
node='test_actual_current_event_fitter_issuer_and_shared_scorer_keep_exact_private_basis@operation-event-native'
log=Path('/var/log/postgresql/postgresql-18-corpus.log')
db='cs_sem_test_2734530_72524f379178'
phases={}
for line in (Path('build/ci')/receipt/'ordinary/reportlog.jsonl').open():
 r=json.loads(line)
 if r.get('nodeid','').endswith(node) and r.get('when') in ('setup','call'):
  phases[r['when']]=(r['start'],r['stop'],r['duration'])
pattern=re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d+) EST \[(\d+)\] (\S+)@'+re.escape(db)+r' LOG:  duration: ([\d.]+) ms  (execute[^:]*:|statement:)\s*(.*)')
rows=[]
for line_no,line in enumerate(log.open(),1):
 m=pattern.match(line)
 if not m: continue
 stamp=datetime.fromisoformat(m[1]+'-05:00').timestamp()
 phase=next((p for p,(start,stop,duration) in phases.items() if start<=stamp<=stop),None)
 if phase is None:continue
 sql=m[6]
 op=re.search(r'\b(ops|sem|data)\.([a-z_]+)\s*\(',sql)
 label=(op[1]+'.'+op[2]) if op else sql.split()[0].upper()
 rows.append(dict(phase=phase,operation=label,seconds=float(m[4])/1000,line=line_no,pid=int(m[2]),principal=m[3]))
summaries=[]
for phase in phases:
 for operation in sorted({r['operation'] for r in rows if r['phase']==phase}):
  selected=[r for r in rows if r['phase']==phase and r['operation']==operation]
  summaries.append(dict(phase=phase,operation=operation,count=len(selected),sum_seconds=round(sum(r['seconds'] for r in selected),6),max_seconds=max(r['seconds'] for r in selected)))
print(json.dumps(dict(receipt=receipt,node=node,database=db,source_log=str(log),threshold_ms=250,phases=phases,statements=rows,summary=summaries,limitations='Logged statement durations may overlap and count only >=250ms. auto_explain plan entries excluded. Source phase timestamps classify statement finish time. Nested plans unavailable.'),indent=2))
