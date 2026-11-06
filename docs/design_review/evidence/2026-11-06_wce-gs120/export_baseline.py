"""Export the completed corpus through bounded ordinary per-source selections."""
from pathlib import Path
from collections import Counter
import json
from sqlalchemy import text
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions, export_contribution_selection
from corpus_structure.serve.structural_products import StructuralRequest, serve_structural_products
from corpus_structure.settings import Settings
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'baseline003-export001';OUT.mkdir(exist_ok=False)
def retain(path,value):path.write_bytes(canonical_bytes(value)+b'\n')
try:
 with open_runtime_engine(Settings(),'gs120-completed-baseline-export',purpose='read') as engine,read_snapshot(engine) as conn:
  views=conn.execute(text('SELECT source_view_id FROM ops.run_source_view WHERE run_id=139 ORDER BY source_view_id')).scalars().all()
  assert len(views)==40
  totals=Counter();selections=[]
  for view in views:
   folder=OUT/('source-'+str(view));folder.mkdir()
   req=ContributionRequest(run_id=139,source_view_id=view,limit=1000,page_bytes=16_000_000,max_bytes=128_000_000)
   pages=[]
   while True:
    page=serve_contributions(conn,req);pages.append(page.model_dump(mode='json'))
    if page.next_cursor is None:break
    req=req.model_copy(update={'cursor':page.next_cursor})
   retain(folder/'pages.json',pages)
   manifest=export_contribution_selection(conn,req.model_copy(update={'cursor':None}),folder/'export')
   retain(folder/'export.json',manifest)
   totals.update(pages[0]['inventory_counts']);selections.append(dict(source_view_id=view,pages=len(pages),inventory_counts=pages[0]['inventory_counts'],manifest=str((folder/'export/manifest.json').relative_to(OUT))))
  structural=serve_structural_products(conn,StructuralRequest(run_id=139,kind='definition_components',max_bytes=8_000_000))
  retain(OUT/'structural-inspection.json',structural.model_dump(mode='json'))
  expected=conn.execute(text('SELECT count(*) FROM kb.source_contribution c JOIN ops.cut_task m ON m.origin_task_id=c.task_id WHERE m.cut_id=178')).scalar_one()
  assert totals['contributions']==expected
  result=dict(outcome='passed',run_id=139,cut_id=178,sources=len(views),inventory_counts=dict(totals),definition_components=sum(len(r.definition_components.components) for r in structural.reports),selections=selections,scope='Bounded ordinary Reader and detached contribution exports, exact completed-cut population reconciliation; private proposals, semantic correctness unassessed')
  retain(OUT/'result.json',result)
  print(json.dumps({k:v for k,v in result.items() if k!='selections'}),flush=True)
except BaseException as error:
 retain(OUT/'failure.json',dict(outcome='failed',type=type(error).__name__,message=str(error)));raise
