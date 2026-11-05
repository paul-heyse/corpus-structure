"""Finish already produced source-ready44 without executing any producer."""
import json
from dataclasses import asdict
from pathlib import Path
from sqlalchemy import select
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.settings import Settings
HERE=Path(__file__).resolve().parent
TARGET=HERE/'raw/contextual-local-publication-002-completion-recovery-001.json'
if TARGET.exists():raise FileExistsError(TARGET)
settings=Settings()
with open_runtime_engine(settings,'pce-contextual-existing-completion',purpose='write') as engine:
    with engine.connect() as conn:
        runs,tasks,projects=map(table,('ops.run','ops.task','data.project'))
        run=dict(conn.execute(select(runs).where(runs.c.id==44)).mappings().one())
        assert run['runtime_id']=='runtime:4044d3bed00caa1ccf38d11f2f1568733f6893cf307186b7ce8d3953b3d19cb1'
        assert run['project_id']=='m1-source-grinstead-snell'
        before=dict(conn.execute(select(projects).where(projects.c.project_id==run['project_id'])).mappings().one())
        inventory=[dict(row) for row in conn.execute(select(tasks.c.id,tasks.c.status,tasks.c.reused_task_id).where(tasks.c.run_id==44)).mappings()]
        assert len(inventory)==2 and all(row['status'] in ('done','empty','reused') for row in inventory)
    completed=finalize_bound_run(engine,44,'contextual-local-publication-002-recovered:contextual:44',analytics=settings.analytics)
    with read_snapshot(engine) as conn:
        page=serve_contributions(conn,ContributionRequest(run_id=44,method='retrieve.contextual',include_publication=True,include_support=True,limit=1000,max_bytes=32000000,page_bytes=8000000))
        after=dict(conn.execute(select(projects).where(projects.c.project_id==run['project_id'])).mappings().one())
    assert before==after
    assert page.inventory_counts['admitted_semantic_claims']==0
    result=dict(outcome='passed',run_id=44,completed=asdict(completed),runtime_id=run['runtime_id'],release_id=run['release_id'],inventory_counts=page.inventory_counts,method_inventory=inventory,project_before=before,project_after=after,project_defaults_preserved=True,producer_execution=False,source_execution=False,annotation_execution=False,scope='finish already produced source-ready44; its new runtime origin is not authorized by old evaluation15, so semantic admission correctly remains zero; fresh grade on retained output is required')
with TARGET.open('x') as out:json.dump(result,out,indent=2);out.write('\n')
print(json.dumps(result),flush=True)
