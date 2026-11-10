"""Read-only custody accounting for the rejected derived-source authority attempt."""
import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import func, select
from corpus_structure.methods.interpretations import AuthoredInterpretationConfig
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

folder=Path(__file__).parent
configuration=json.loads((folder/'raw/source-journey-03/measurement-recognition-input.json').read_bytes())
cfg=AuthoredInterpretationConfig.model_validate(configuration)
release=cfg.reviews[0]['vocabulary_release']
realization='interpretation-input:'+sha256(canonical_bytes([release,'measurement',cfg.model_dump(mode='json')])).hexdigest()
report=dict(attempt_run_id=494, reason='structural source differs from original completed source custody', realization_id=realization)
with open_runtime_engine(Settings(),'dmc-failed-custody-disposition',purpose='read') as engine,read_snapshot(engine) as conn:
    counts={}
    for name,key in [('ops.run','id'),('ops.task','run_id'),('ops.input_cut','run_id'),('ops.completed_result','run_id'),('ops.run_source_view','run_id')]:
        t=table(name);counts[name]=conn.scalar(select(func.count()).select_from(t).where(t.c[key]==494))
    report['committed_rows_for_run494']=counts
    t=table('data.realization')
    row=conn.execute(select(t).where(t.c.release_id==release,t.c.realization_id==realization)).mappings().one_or_none()
    report['retained_input_realization']=dict(row) if row else None
    p=table('data.project')
    project=conn.execute(select(p).where(p.c.project_id==cfg.source.project_id)).mappings().one()
    report['input_realization_referenced_by_project_fields']=[k for k,v in project.items() if v==realization]
    t=table('data.source_record')
    report['input_realization_record_count']=conn.scalar(select(func.count()).select_from(t).where(t.c.release_id==release,t.c.realization_id==realization))
assert all(v==0 for v in counts.values())
assert report['input_realization_record_count']==0 and not report['input_realization_referenced_by_project_fields']
report['conclusion']='Run494 allocation rolled back on source custody refusal; no committed run/task/cut/result/view selection. Empty unselected input realization from earlier ordinary initialization remains retained; no cleanup or relabeling performed.'
(folder/'raw/run494-custody-disposition.json').write_text(json.dumps(report,sort_keys=True,default=str))
print(json.dumps(report,sort_keys=True,default=str))
