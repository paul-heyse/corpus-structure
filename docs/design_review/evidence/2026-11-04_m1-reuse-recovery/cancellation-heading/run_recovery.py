"""Recover the actual cancelled heading via a new run after native125 admission."""
from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
import json
import multiprocessing
import os
from pathlib import Path
import threading
import time
import traceback

from sqlalchemy import func, select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.m1 import registry, source_graph
from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.operations import OperationBinding, run_view
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

from run_probe import now, process_identity, serial, tasks, write

ROOT = Path(__file__).parent


def main():
    folder = ROOT / 'attempt-002'
    folder.mkdir(exist_ok=False)
    declared = json.loads((ROOT / 'attempt-001' / 'declared-input.json').read_bytes())
    inventory = json.loads((ROOT / 'source-inventory.json').read_bytes())
    source = declared['source']
    dependencies = inventory['dependencies']
    configs = declared['configs']
    scope = declared['scope']
    frozen_configuration = declared['extraction_policy_config']
    assert declared['fresh'] == ['extract.m1_candidates']
    assert configs['extract.m1_candidates']['readings']['parent_threads'] == 1
    assert configs['extract.m1_candidates']['readings']['threads'] == 4
    state = dict(run_id=None, child=None, observer_error=None)
    stop = threading.Event()
    event_lock = threading.Lock()
    settings = Settings()

    def event(kind, **data):
        with event_lock, (folder / 'events.jsonl').open('a') as output:
            output.write(json.dumps(dict(at=now(), monotonic=time.monotonic(),
                event=kind, **serial(data))) + '\n')

    with open_runtime_engine(settings, 'm1-heading-recovery-native125', purpose='write') as engine:
        runs, project = table('ops.run'), table('data.project')
        with engine.connect() as conn:
            prepared = open_release(conn, source['release_id'])
            predecessors = {row['id']: dict(row) for row in conn.execute(
                select(runs).where(runs.c.id.in_((17, 18)))).mappings()}
            before = dict(conn.execute(select(project).where(
                project.c.project_id == source['project_id'])).mappings().one())
            native_function = conn.execute(text(
                "SELECT pg_get_functiondef('ops.select_reused_source_views(bigint,bigint)'::regprocedure)"
            )).scalar_one()
        assert predecessors[17]['status'] == 'cancelled'
        assert predecessors[18]['status'] == 'failed'
        assert before['selected_result_run_id'] is None
        assert "v.native_task_id = origin.id" in native_function or 'v.native_task_id=origin.id' in native_function
        assert 'retained_product=jsonb_build_object' in native_function or 'retained_product = jsonb_build_object' in native_function
        write(folder / 'declared-input.json', dict(source_attempt='attempt-001',
            source_run=14, cancelled_run=17, failed_run=18, native_head='125',
            declared=declared, before=before, native_function_sha256=sha256(native_function.encode()).hexdigest()))
        (folder / 'live-source-reuse-function.sql').write_text(native_function)
        base = registry(Path('domains/statistics'))
        bound = MethodRegistry(base.methods(), replace(base.file, configs=configs),
                               base.sources, prepared=prepared)

        def observe():
            try:
                deadline = time.monotonic() + 180
                while not stop.wait(0.05):
                    if time.monotonic() > deadline:
                        raise TimeoutError('actual recovery child not observed within180s')
                    if state['run_id'] is None:
                        with engine.connect() as conn:
                            ids = conn.execute(select(runs.c.id).where(
                                runs.c.id > 18, runs.c.project_id == source['project_id'],
                                runs.c.options['scope']['name'].astext == scope['name'])).scalars().all()
                        if len(ids) > 1:
                            raise RuntimeError('multiple new runs share owned recovery scope')
                        if ids:
                            state['run_id'] = ids[0]
                            event('owned_recovery_run_observed', run_id=ids[0])
                    children = [child for child in multiprocessing.active_children()
                                if child.name == 'native-gliner-cpu']
                    if len(children) > 1:
                        raise RuntimeError('multiple owned recovery model children')
                    if children and state['run_id'] is not None:
                        child = process_identity(children[0].pid)
                        assert child['ppid'] == os.getpid()
                        with engine.connect() as conn:
                            active_tasks = tasks(conn, state['run_id'])
                        candidate = [task for task in active_tasks
                                     if task['method'] == 'extract.m1_candidates' and task['status'] == 'running']
                        assert len(candidate) == 1 and candidate[0]['unit_id'] == 22
                        state['child'] = child
                        event('actual_recovery_model_child_observed', child=child, tasks=active_tasks)
                        return
            except BaseException as error:
                state['observer_error'] = repr(error)
                event('observer_failed', exception=repr(error))

        watcher = threading.Thread(target=observe, name='recovery-owned-child-observer')
        started = time.monotonic()
        watcher.start()
        try:
            report = run_source_methods(
                engine, project_id=source['project_id'], prepared=prepared,
                binding=OperationBinding(source['release_id'], source['input_realization_id'],
                    source['input_revision'], canonical_bytes(dependencies['parent'])),
                registry=bound, graph=source_graph('readings'),
                method_settings=MethodSettings(data_dir=settings.paths.data_dir,
                                              model_cache=settings.paths.model_cache),
                guideline=dependencies['guideline'], corpus_record=dependencies['corpus'],
                scope_record=scope, policy_source=dependencies['policy'],
                fresh=tuple(declared['fresh']), extraction_policy='m1-candidate',
                extraction_policy_config=frozen_configuration,
                configurations={'extract.m1_candidates': 'readings'})
        except BaseException as error:
            write(folder / 'exception.json', dict(at=now(), exception=type(error).__name__,
                message=str(error), traceback=traceback.format_exc(), state=state))
            raise
        finally:
            stop.set()
            watcher.join(timeout=15)
        assert not watcher.is_alive()
        assert state['observer_error'] is None, state['observer_error']
        assert state['run_id'] == report.run_id
        assert state['child'] is not None
        child_after = process_identity(state['child']['pid'])
        assert child_after.get('absent'), child_after
        assert not [child for child in multiprocessing.active_children() if child.name == 'native-gliner-cpu']
        write(folder / 'source-ready.json', dict(report=report.model_dump(mode='json'),
            elapsed_seconds=time.monotonic() - started, child=state['child'], child_after=child_after))
        event('recovery_source_ready_child_settled', report=report.model_dump(mode='json'), child_after=child_after)
        with engine.connect() as conn:
            recovery_run = dict(conn.execute(select(runs).where(runs.c.id == report.run_id)).mappings().one())
            recovered_tasks = tasks(conn, report.run_id)
            refs = run_view(conn, report.run_id, prepared).reader.source_views()
            task_table = table('ops.task')
            prior_task_links = [dict(row) for row in conn.execute(select(task_table.c.id,
                task_table.c.run_id, task_table.c.status, task_table.c.reused_task_id,
                task_table.c.result_digest).where(task_table.c.id.in_((34, 69, 70, 71, 72)))).mappings()]
            result_table = table('ops.task_result')
            candidate_task = next(task for task in recovered_tasks if task['method'] == 'extract.m1_candidates')
            parse_detail = conn.execute(select(result_table.c.body['parse_detail']).where(
                result_table.c.task_id == candidate_task['id'])).scalar_one()
            detail = source_python(parse_detail)
            native_reports = [entry['report'] for entry in detail.get('reports', ()) if 'report' in entry]
            execution = dict(native_calls=len(native_reports),
                cold_calls=sum(not item['resident_reused'] for item in native_reports),
                native_inference_seconds=sum(item['inference_seconds'] for item in native_reports),
                contexts=len(detail.get('contexts', ())),
                max_input_bytes=max((item['preparation']['input_bytes'] for item in native_reports), default=0),
                source_roles=[dict(family=item['family'], outcome=item['outcome']) for item in detail.get('execution', ())])
        assert recovery_run['dependencies'] == predecessors[17]['dependencies'] == predecessors[18]['dependencies']
        assert recovery_run['dependency_digest'] == predecessors[17]['dependency_digest']
        assert [ref.id for ref in refs] == [22]
        ingest = next(task for task in recovered_tasks if task['method'] == 'ingest.pdf_integrated')
        annotation = next(task for task in recovered_tasks if task['method'] == 'extract.m1_annotations')
        assert ingest['status'] == 'reused' and ingest['reused_task_id'] == 69
        assert annotation['status'] == 'reused' and annotation['reused_task_id'] == 34
        assert candidate_task['status'] in ('done', 'empty') and candidate_task['reused_task_id'] is None
        assert execution['native_calls'] == 3 and execution['cold_calls'] == 1
        assert all(task['reused_task_id'] != 71 for task in recovered_tasks)
        write(folder / 'source-task-origin-links.json', serial(dict(tasks=recovered_tasks,
            predecessor_links=prior_task_links, selected_views=[asdict(ref) for ref in refs],
            execution=execution, dependency_bytes_equal=True,
            dependency_digest=recovery_run['dependency_digest'])))
        output_id = 'm1-heading-recovery:' + str(report.run_id)
        result = finalize_bound_run(engine, report.run_id, output_id)
        with engine.connect() as conn:
            after = dict(conn.execute(select(project).where(
                project.c.project_id == source['project_id'])).mappings().one())
            final_run = dict(conn.execute(select(runs).where(runs.c.id == report.run_id)).mappings().one())
            final_tasks = tasks(conn, report.run_id)
            cancelled_counts = {name: conn.execute(select(func.count()).select_from(table(name)).where(
                table(name).c.task_id == 71)).scalar_one() for name in ('ops.task_result', 'kb.observation')}
            cut_tasks = table('ops.cut_task')
            cuts = table('ops.input_cut')
            final_cut_links = [dict(row) for row in conn.execute(select(cut_tasks).join(
                cuts, cuts.c.id == cut_tasks.c.cut_id).where(cuts.c.run_id == report.run_id,
                cuts.c.final)).mappings()]
        assert after == before and after['selected_result_run_id'] is None
        assert final_run['status'] == 'finished' and final_run['result_realization_id'] == output_id
        assert all(task['status'] not in ('pending', 'running', 'awaiting_agent') for task in final_tasks)
        assert all(row['origin_task_id'] != 71 and row['task_id'] != 71 for row in final_cut_links)
        assert all(count == 0 for count in cancelled_counts.values())
        summary = serial(dict(outcome='passed', at=now(), native_head='125',
            predecessor_cancelled_run=17, predecessor_failed_run=18, recovered_run=report.run_id,
            release_id=source['release_id'], input_realization_id=source['input_realization_id'],
            frozen_source_scope_config_dependencies_equal=True, selected_source_views=[22],
            execution=execution, child=state['child'], child_after=child_after,
            source_tasks=final_tasks, final_cut_links=final_cut_links,
            cancelled_task71_counts=cancelled_counts, publication=asdict(result),
            nondefault=True, selected_before=before, selected_after=after, open_owned_tasks=[],
            elapsed_seconds=time.monotonic()-started,
            limits=['run17/task71 cancellation was completion-fenced; inference interruption not demonstrated',
                    'new-run recovery, not same-run continuation or exact completion receipt replay',
                    'heading22 only; no source quality or all-family qualification']))
        write(folder / 'summary.json', summary)
        event('recovery_published_nondefault', run_id=report.run_id, output=output_id)
        print(json.dumps(dict(outcome='passed', recovered_run=report.run_id,
            output_realization=output_id, native_calls=execution['native_calls'],
            nondefault=True, no_open_owned_tasks=True)), flush=True)


if __name__ == '__main__':
    main()
