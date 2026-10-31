"""Native SymPy compatibility on recognized formulas, with bounded calls."""
import json,signal
from pathlib import Path
from sympy.parsing.latex import parse_latex
B=Path(__file__).resolve().parent
rows=[]
def expired(*a):raise TimeoutError('2 second formula budget')
signal.signal(signal.SIGALRM,expired)
for p in sorted((B/'raw').glob('*.document.json')):
 d=json.loads(p.read_text())
 for item in [i for i in d.get('texts',[]) if i.get('label')=='formula'][:5]:
  if item.get('label')!='formula':continue
  text=item['text'];row={'document':p.name,'ref':item['self_ref'],'text':text}
  signal.setitimer(signal.ITIMER_REAL,2)
  try:
   value=parse_latex(text,backend='lark');row.update(outcome='available',native_type=type(value).__name__,native=str(value))
  except Exception as e:row.update(outcome='unsupported_or_failed',error_type=type(e).__name__,error=str(e)[:300])
  finally:signal.setitimer(signal.ITIMER_REAL,0)
  rows.append(row)
(B/'raw/math-results.json').write_text(json.dumps(rows,indent=2));print('formula cases',len(rows),'native available',sum(r['outcome']=='available' for r in rows))
