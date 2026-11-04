"""Actual retained-heading cancellation and new-run recovery; no reference inputs."""
from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import multiprocessing
import os
from pathlib import Path
import threading
import time
import traceback

import yaml
from sqlalchemy import select

from corpus_structure.core.canonical import digest
from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.commands import cancel_bound_run, finalize_bound_run
from corpus_structure.orchestrate.m1 import registry, source_graph
from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, run_view
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

ROOT = Path(__file__).parent


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.write_bytes(canonical_bytes(value))


def process_identity(pid):
    try:
        stat = Path(f'/proc/{pid}/stat').read_text()
        suffix = stat[stat.rfind(')') + 2:].split()
        return dict(pid=pid, state=suffix[0], ppid=int(suffix[1]), start_ticks=int(suffix[19]),
                    cmdline=Path(f'/proc/{pid}/cmdline').read_bytes().decode().replace('\0', ' '))
    except FileNotFoundError:
        return dict(pid=pid, absent=True)


def tasks(conn, run_id):
    t, c, m = map(table, ('ops.task', 'ops.method_config', 'ops.method'))
    return [dict(row) for row in conn.execute(
        select(t.c.id, t.c.run_id, m.c.name.label('method'), t.c.unit_id,
               t.c.status, t.c.attempt, t.c.claimed_by, t.c.reused_task_id,
               t.c.input_hash, t.c.result_digest, t.c.error, t.c.reason,
               t.c.started_at, t.c.finished_at)
        .join(c, t.c.method_config_id == c.c.id).join(m, c.c.method_id == m.c.id)
        .where(t.c.run_id == run_id).order_by(t.c.id)).mappings()]


def serial(value):
    return json.loads(json.dumps(value, default=str))


def main():
    folder = ROOT / 'attempt-001'
    folder.mkdir(exist_ok=False)
    settings = Settings()
    inventory = json.loads((ROOT / 'source-inventory.json').read_bytes())
    original = inventory['run14']
    dependencies = inventory['dependencies']
    heading = inventory['section']['name']
    scope = dict(kind='native_sections', name='m1-actual-cancel-heading-20261104-001',
                 sections=[heading], include_descendants=False, hash=digest([heading]))
    configs = {name: {'readings' if name == 'extract.m1_candidates' else 'default':
                     dict(row['parameters'])} for name, row in dependencies['operations'].items()}
    candidate = configs['extract.m1_candidates']['readings']
    assert candidate['parent_threads'] == 1 and candidate['threads'] == 4
    assert inventory['heading']['native_product']['content_digest'] == 'e8ee2f72912fe174fdaf76918b7cb347ad245fecdf9c827688814729b9961cba'
    events = folder / 'events.jsonl'
    event_lock = threading.Lock()

    def event(kind, **data):
        with event_lock, events.open('a') as out:
            out.write(json.dumps(dict(at=now(), monotonic=time.monotonic(), event=kind,
                                      **serial(data))) + '\n')

    state = dict(run_id=None, child=None, cancellation=None, monitor_error=None)
    stop = threading.Event()
    with open_runtime_engine(settings, 'm1-actual-cancellation-heading', purpose='write') as engine:
        with engine.connect() as conn:
            prepared = open_release(conn, original['release_id'])
            project = table('data.project')
            before = dict(conn.execute(select(project).where(project.c.project_id == original['project_id'])).mappings().one())
        base = registry(Path('domains/statistics'))
        configuration_source = yaml.safe_dump(dict(version=base.file.version, configs=configs,
                                                   **base.file.sections), sort_keys=True)
        declared = dict(started_at=now(), source_run=14, source=original,
                        native=inventory['heading'], heading=heading, scope=scope, configs=configs,
                        extraction_policy_config=configuration_source,
                        fresh=['extract.m1_candidates'], parent_threads=1, model_threads=4,
                        configuration_sha256=sha256(configuration_source.encode()).hexdigest(),
                        invocation='run_source_methods(source_graph(readings))', selected_before=before)
        write(folder / 'declared-input.json', declared)

        def invoke():
            bound = MethodRegistry(base.methods(), replace(base.file, configs=configs),
                                   base.sources, prepared=prepared)
            return run_source_methods(
                engine, project_id=original['project_id'], prepared=prepared,
                binding=OperationBinding(original['release_id'], original['input_realization_id'],
                    original['input_revision'], canonical_bytes(dependencies['parent'])),
                registry=bound, graph=source_graph('readings'),
                method_settings=MethodSettings(data_dir=settings.paths.data_dir,
                                              model_cache=settings.paths.model_cache),
                guideline=dependencies['guideline'], corpus_record=dependencies['corpus'],
                scope_record=scope, policy_source=dependencies['policy'],
                fresh=('extract.m1_candidates',), extraction_policy='m1-candidate',
                extraction_policy_config=configuration_source,
                configurations={'extract.m1_candidates': 'readings'})

        def monitor():
            try:
                deadline = time.monotonic() + 240
                while not stop.wait(0.05):
                    if time.monotonic() > deadline:
                        raise TimeoutError('owned startup observation exceeded 240 seconds')
                    if state['run_id'] is None:
                        with engine.connect() as conn:
                            r = table('ops.run')
                            ids = conn.execute(select(r.c.id).where(
                                r.c.project_id == original['project_id'],
                                r.c.options['scope']['name'].astext == scope['name'])).scalars().all()
                        if len(ids) > 1:
                            raise RuntimeError('scope already has multiple runs before recovery')
                        if ids:
                            state['run_id'] = ids[0]
                            event('owned_run_observed', run_id=ids[0])
                    children = [p for p in multiprocessing.active_children()
                                if p.name == 'native-gliner-cpu']
                    if len(children) > 1:
                        raise RuntimeError('probe has multiple model children')
                    if state['run_id'] is not None and children:
                        child = process_identity(children[0].pid)
                        if child.get('ppid') != os.getpid():
                            raise RuntimeError('model child parent mismatch')
                        state['child'] = child
                        with engine.connect() as conn:
                            live_tasks = tasks(conn, state['run_id'])
                        active = [t for t in live_tasks if t['status'] == 'running' and t['method'] == 'extract.m1_candidates']
                        if len(active) != 1 or active[0]['unit_id'] != 22:
                            raise RuntimeError('model startup is outside exact selected heading')
                        event('actual_model_child_observed', child=child, tasks=live_tasks)
                        requested = time.monotonic()
                        report = cancel_bound_run(engine, state['run_id'])
                        state['cancellation'] = report.model_dump(mode='json')
                        event('cancel_bound_run_returned', report=state['cancellation'],
                              elapsed_seconds=time.monotonic() - requested,
                              child_after_request=process_identity(child['pid']))
                        return
            except BaseException as error:
                state['monitor_error'] = repr(error)
                event('monitor_failed', exception=repr(error))
                if state['run_id'] is not None:
                    cancel_bound_run(engine, state['run_id'])

        watcher = threading.Thread(target=monitor, name='probe-owned-run-observer')
        watcher.start()
        try:
            first = invoke()
            event('unexpected_cancel_attempt_completed', report=first.model_dump(mode='json'))
        except BaseException as error:
            write(folder / 'cancellation-exception.json', dict(exception=type(error).__name__,
                message=str(error), notes=getattr(error, '__notes__', []), traceback=traceback.format_exc()))
            event('cancelled_source_invocation_settled', exception=type(error).__name__, message=str(error))
        finally:
            stop.set()
            watcher.join(timeout=15)
        assert not watcher.is_alive(), 'observer did not settle'
        assert state['monitor_error'] is None, state['monitor_error']
        assert state['run_id'] is not None and state['cancellation'] is not None
        assert state['child'] is not None
        child_after = process_identity(state['child']['pid'])
        assert child_after.get('absent'), child_after
        with engine.connect() as conn:
            r = table('ops.run')
            closed = dict(conn.execute(select(r).where(r.c.id == state['run_id'])).mappings().one())
            closed_tasks = tasks(conn, state['run_id'])
        write(folder / 'cancellation-settled.json', serial(dict(state=state,
            run=closed, tasks=closed_tasks, child_after=child_after, at=now())))
        assert closed['status'] in ('cancelled', 'failed')
        assert closed['result_realization_id'] is None
        assert all(t['status'] not in ('running', 'pending', 'awaiting_agent') for t in closed_tasks)
        try:
            finalize_bound_run(engine, state['run_id'], 'm1-cancelled-refusal:' + str(state['run_id']))
        except Exception as error:
            write(folder / 'closed-finalization-refusal.json', dict(run_id=state['run_id'],
                exception=type(error).__name__, message=str(error), at=now()))
        else:
            raise AssertionError('closed run unexpectedly finalized')
        event('recovery_started', closed_run=state['run_id'])
        recovered = invoke()
        write(folder / 'recovered-source-ready.json', recovered.model_dump(mode='json'))
        with engine.connect() as conn:
            recovered_run = dict(conn.execute(select(r).where(r.c.id == recovered.run_id)).mappings().one())
            recovered_tasks = tasks(conn, recovered.run_id)
            refs = run_view(conn, recovered.run_id, prepared).reader.source_views()
        assert [ref.id for ref in refs] == [22]
        assert recovered_run['dependencies'] == closed['dependencies']
        assert recovered_run['dependency_digest'] == closed['dependency_digest']
        cancelled_ids = {t['id'] for t in closed_tasks if t['status'] not in ('done', 'empty', 'reused')}
        assert all(t['reused_task_id'] not in cancelled_ids for t in recovered_tasks)
        raw = [t for t in recovered_tasks if t['method'] == 'extract.m1_candidates']
        assert len(raw) == 1 and raw[0]['status'] in ('empty', 'done') and raw[0]['reused_task_id'] is None
        write(folder / 'recovered-task-links.json', serial(dict(run=recovered_run,
              tasks=recovered_tasks, cancelled_task_ids=sorted(cancelled_ids),
              selected_views=[asdict(ref) for ref in refs])))
        output = 'm1-heading-recovery:' + str(recovered.run_id)
        result = finalize_bound_run(engine, recovered.run_id, output)
        with engine.connect() as conn:
            after = dict(conn.execute(select(project).where(project.c.project_id == original['project_id'])).mappings().one())
            final = dict(conn.execute(select(r).where(r.c.id == recovered.run_id)).mappings().one())
        assert after['selected_result_run_id'] != recovered.run_id
        assert final['status'] == 'finished'
        write(folder / 'summary.json', serial(dict(outcome='passed', at=now(),
            scope='actual heading22 cancellation/fencing/new-run CPU recovery only',
            cancelled_run=state['run_id'], recovered_run=recovered.run_id,
            frozen_dependencies_equal=True, selected_views=[22],
            child_before_cancel=state['child'], child_after_settlement=child_after,
            cancelled_task_ids=sorted(cancelled_ids), publication=asdict(result),
            selected_before=before, selected_after=after, final_run=final,
            no_cancelled_task_reuse=True, nondefault=True,
            phase_limits=['no native inference phase timing claim for cancelled child',
                          'no all-family quality claim', 'no receipt-replay recovery claim',
                          'no same-run source continuation API exercised'])))
        event('recovery_published_nondefault', run_id=recovered.run_id, output=output)
        print(json.dumps(dict(outcome='passed', cancelled_run=state['run_id'],
                              recovered_run=recovered.run_id, output=output)), flush=True)


if __name__ == '__main__':
    main()
