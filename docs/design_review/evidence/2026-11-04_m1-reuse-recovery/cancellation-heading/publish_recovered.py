"""Normal restricted native admission, then finalize the already-ready recovery run."""
from dataclasses import asdict
from pathlib import Path
import json

from sqlalchemy import func, select

from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.execution_admission import require_native_execution
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import run_view
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

from run_probe import now, process_identity, serial, tasks, write

ROOT = Path(__file__).parent
FOLDER = ROOT / 'attempt-002'
RUN = 19
OUTPUT = 'm1-heading-recovery:19'


def main():
    declared = json.loads((FOLDER / 'declared-input.json').read_bytes())
    source = declared['declared']['source']
    ready = json.loads((FOLDER / 'source-ready.json').read_bytes())
    links = json.loads((FOLDER / 'source-task-origin-links.json').read_bytes())
    settings = Settings()
    with open_runtime_engine(settings, 'm1-recovery-native125-admit', purpose='admit') as engine:
        with engine.begin() as conn:
            prepared = open_release(conn, source['release_id'])
            require_native_execution(conn, prepared)
    write(FOLDER / 'restricted-admission.json', dict(outcome='passed', at=now(),
        api='execution_admission.require_native_execution', purpose='admit',
        release_id=source['release_id'], native_head='125',
        meaning='exact deployed native enforcement readmission; no default activation'))
    with open_runtime_engine(settings, 'm1-recovery-native125-publish', purpose='write') as engine:
        result = finalize_bound_run(engine, RUN, OUTPUT)
        write(FOLDER / 'publication.json', serial(asdict(result)))
        replayed = finalize_bound_run(engine, RUN, OUTPUT)
        write(FOLDER / 'completed-finalization-replay.json', serial(dict(
            outcome='passed', at=now(), first=asdict(result), replayed=asdict(replayed),
            scope='completed cut publication receipt re-read; not source-task completion replay')))
        assert asdict(result) == asdict(replayed)
        with engine.connect() as conn:
            runs, project = table('ops.run'), table('data.project')
            final_run = dict(conn.execute(select(runs).where(runs.c.id == RUN)).mappings().one())
            final_tasks = tasks(conn, RUN)
            refs = run_view(conn, RUN, prepared).reader.source_views()
            after = dict(conn.execute(select(project).where(
                project.c.project_id == source['project_id'])).mappings().one())
            cut_tasks, cuts = table('ops.cut_task'), table('ops.input_cut')
            cut_links = [dict(row) for row in conn.execute(select(cut_tasks).join(
                cuts, cuts.c.id == cut_tasks.c.cut_id).where(cuts.c.run_id == RUN,
                cuts.c.final)).mappings()]
            cancelled_counts = {name: conn.execute(select(func.count()).select_from(table(name)).where(
                table(name).c.task_id == 71)).scalar_one() for name in ('ops.task_result', 'kb.observation')}
            own_open = [dict(row) for row in conn.execute(select(table('ops.task').c.id,
                table('ops.task').c.run_id, table('ops.task').c.status).where(
                table('ops.task').c.run_id.in_((17, 18, 19)),
                table('ops.task').c.status.in_(('pending', 'running', 'awaiting_agent')))).mappings()]
            states = [dict(row) for row in conn.execute(select(runs.c.id, runs.c.status,
                runs.c.result_realization_id, runs.c.sealed).where(runs.c.id.in_((17, 18, 19)))).mappings()]
        assert final_run['status'] == 'finished' and final_run['result_realization_id'] == OUTPUT
        assert after == declared['before'] and after['selected_result_run_id'] is None
        assert [ref.id for ref in refs] == [22]
        assert not own_open
        assert all(row['origin_task_id'] != 71 and row['task_id'] != 71 for row in cut_links)
        assert all(count == 0 for count in cancelled_counts.values())
        child_after = process_identity(ready['child']['pid'])
        assert child_after.get('absent'), child_after
        summary = serial(dict(outcome='passed', at=now(), native_head='125',
            predecessor_cancelled_run=17, predecessor_failed_run=18, recovered_run=RUN,
            release_id=source['release_id'], input_realization_id=source['input_realization_id'],
            frozen_source_scope_config_dependencies_equal=links['dependency_bytes_equal'],
            dependency_digest=links['dependency_digest'], selected_source_views=[22],
            execution=links['execution'], child=ready['child'], child_after=child_after,
            source_seconds=ready['elapsed_seconds'], source_tasks=final_tasks,
            predecessor_links=links['predecessor_links'], final_cut_links=cut_links,
            cancelled_task71_counts=cancelled_counts, publication=asdict(result),
            completed_finalization_receipt_replay='passed', nondefault=True,
            selected_before=declared['before'], selected_after=after,
            open_owned_tasks=own_open, run_states=states,
            retained_publication_refusal='attempt-002.log',
            admission_recovery='restricted-admission.json',
            limits=['run17/task71 cancellation was completion-fenced; inference interruption not demonstrated',
                    'new-run source recovery; no same-run continuation',
                    'completed finalization replay; no exact source-completion receipt replay',
                    'heading22 only; no extraction quality or all-family qualification']))
        write(FOLDER / 'summary.json', summary)
        print(json.dumps(dict(outcome='passed', recovered_run=RUN,
            output_realization=OUTPUT, native_calls=links['execution']['native_calls'],
            nondefault=True, no_open_owned_tasks=True, finalization_receipt_replay='passed')))


if __name__ == '__main__':
    main()
