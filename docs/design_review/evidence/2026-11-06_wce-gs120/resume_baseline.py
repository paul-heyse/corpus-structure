"""Finish interrupted native publication and export, reusing all completed extraction."""
from pathlib import Path
import json
from sqlalchemy import select
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic._operation_ids import CutId
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions, export_contribution_selection
from corpus_structure.serve.structural_products import StructuralRequest, serve_structural_products
from corpus_structure.settings import Settings
HERE=Path(__file__).resolve().parent
OUT=HERE/'baseline003-resume001'
OUT.mkdir(exist_ok=False)
def retain(name,value):
    (OUT/name).write_bytes(canonical_bytes(value)+b'\n')
try:
    with open_runtime_engine(Settings(),'gs120-baseline-resume139',purpose='write') as engine:
        with read_snapshot(engine) as conn:
            before=dict(conn.execute(select(table('ops.run')).where(table('ops.run').c.id==139)).mappings().one())
            assert before['sealed'] and before['status'] in {'consolidating','finished'}
            t,r=table('ops.task'),table('ops.task_result')
            rows=[dict(row) for row in conn.execute(select(t.c.id,t.c.unit_type,r.c.body).join(r,r.c.task_id==t.c.id).where(t.c.run_id==139)).mappings()]
            assert len(rows)==81
            retain('raw-task-envelopes.json',rows)
        print('Resuming consolidation139/cut178; all81 results preserved',flush=True)
        result=consolidate_cut(engine,CutId(178),'gs120-baseline:139')
        retain('consolidation-result.json',dict(run_id=139,cut_id=178,result=str(result),outcome='passed'))
        print('Native consolidation passed; exporting completed cut',flush=True)
        with read_snapshot(engine) as conn:
            request=ContributionRequest(run_id=139,limit=1000,page_bytes=8_000_000)
            pages=[]
            while True:
                page=serve_contributions(conn,request);pages.append(page.model_dump(mode='json'))
                if page.next_cursor is None:break
                request=request.model_copy(update={'cursor':page.next_cursor})
            retain('contributions.json',pages)
            retain('contribution-export.json',export_contribution_selection(conn,ContributionRequest(run_id=139),OUT/'contribution-export'))
            structural=serve_structural_products(conn,StructuralRequest(run_id=139,kind='definition_components',max_bytes=8_000_000))
            retain('structural-inspection.json',structural.model_dump(mode='json'))
        retain('result.json',dict(outcome='passed',run_id=139,cut_id=178,task_results=81,contribution_inventory=pages[0]['inventory_counts'],components=sum(len(r.definition_components.components) for r in structural.reports),standing='private_unassessed',scope='Completed native publication and ordinary export; semantic quality unassessed; original interruption preserved'))
except BaseException as error:
    retain('failure.json',dict(outcome='failed',type=type(error).__name__,message=str(error)))
    raise
