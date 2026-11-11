"""Observe existing task/source metadata for this exact resumed book invocation.

No instrumentation, inference, producer mutation, reference-answer/grade access or
latest-product selection. Run IDs come only from the coordinator's invocation log;
this operating account never substitutes for the exact final combined-view account.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from account_book import HERE, PROJECT, RELEASE, write


def main():
    log=Path('build/tc11-book-execution.log').read_bytes()
    events=[]
    for line in log.decode(errors='replace').splitlines():
        if not line.startswith('{"created":'):continue
        event=json.loads(line)['created']
        if event['project']!=PROJECT or event['release_id']!=RELEASE:
            raise ValueError('execution log mixes another project/release')
        events.append(event['run_id'])
    ids=list(dict.fromkeys(events))
    source=json.loads((HERE/'source-coverage.json').read_bytes())
    captured={row['source_view_id']:row for row in source['source_views']}
    with open_runtime_engine(Settings(),'tc11-book-existing-progress',purpose='read') as engine,read_snapshot(engine) as conn:
        run,task,cfg,method,member=(table(n) for n in ('ops.run','ops.task','ops.method_config','ops.method','ops.run_source_view'))
        states=list(conn.execute(select(run.c.id,run.c.status,task.c.id.label('task_id'),task.c.status.label('task_status'),method.c.name,task.c.started_at,task.c.finished_at,task.c.error).join(task,task.c.run_id==run.c.id).join(cfg,cfg.c.id==task.c.method_config_id).join(method,method.c.id==cfg.c.method_id).where(run.c.id.in_(ids),run.c.project_id==PROJECT).order_by(run.c.id,task.c.id)).mappings())
        memberships=list(conn.execute(select(member.c.run_id,member.c.source_view_id).where(member.c.run_id.in_(ids)).order_by(member.c.run_id,member.c.position)).mappings())
    by_run=defaultdict(list)
    for row in memberships:
        if row['source_view_id'] not in captured:raise ValueError('resumed source scope escapes frozen316')
        by_run[row['run_id']].append(row['source_view_id'])
    seen={identity for values in by_run.values() for identity in values}
    composed=set();stages=defaultdict(Counter);details=[]
    for row in states:
        stages[row['name']][row['task_status']]+=1
        if row['name']=='text.compose_view' and row['task_status'] in {'done','reused'}:composed.update(by_run[row['id']])
        detail={key:(value.isoformat() if isinstance(value,datetime) else value) for key,value in row.items()}
        detail['source_views']=[dict(source_view_id=i,projected_text_chars=captured[i]['projected_text_chars'],piece_kinds=captured[i]['piece_kinds'],analysis_eligible=captured[i]['analysis_eligible']) for i in by_run[row['id']]]
        details.append(detail)
    write('raw/operating-task-source-scopes.json',details)
    result=dict(version='tc11-existing-book-operating-account-1',acquired_at=datetime.now(timezone.utc).isoformat(),project=PROJECT,release_id=RELEASE,capture_run=496,source_cut=614,log_path='build/tc11-book-execution.log',observed_log_bytes=len(log),observed_log_sha256=sha256(log).hexdigest(),created_run_ids=ids,expected_source_views=316,observed_source_view_ids=sorted(seen),locally_composed_source_view_ids=sorted(composed),source_views_without_observed_stage=sorted(set(captured)-seen),source_views_without_completed_local_compose=sorted(set(captured)-composed),stage_task_status_counts={key:dict(value) for key,value in stages.items()},latest_created_run_ids=ids[-12:],active_tasks=[row for row in details if row['task_status'] not in {'done','reused','cancelled','failed'}],recorded_failed_tasks=[row for row in details if row['task_status']=='failed'],final_book_result_exists=(HERE.parent/'book-result.json').exists(),qualification_limit='Only existing task/run/source metadata from this logged invocation. Local stage or compose completion does not establish whole-book combined composition, semantic grades, family examination or source completeness. Frozen source health remains in source-coverage.json.')
    write('operating-account.json',result)
    print(json.dumps({key:result[key] for key in ('acquired_at','created_run_ids','observed_source_view_ids','locally_composed_source_view_ids','stage_task_status_counts','active_tasks','recorded_failed_tasks','final_book_result_exists')}))


if __name__=='__main__':main()
