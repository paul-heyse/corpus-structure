"""Read-only task/output custody and completed CLI replay verification for runs14/16."""
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from sqlalchemy import Text, cast, func, select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import selected_source_views
from corpus_structure.settings import Settings

ROOT = Path(__file__).parent
OUTPUT = ROOT / 'downstream-subset-001' / 'verification.json'


def serial(value):
    return json.loads(json.dumps(value, default=str))


def sql_json_digest(column):
    return func.encode(func.sha256(func.convert_to(cast(column, Text), 'UTF8')), 'hex')


def main():
    assert not OUTPUT.exists(), 'preserve prior verification receipt'
    baseline = json.loads((ROOT.parent / '2026-11-04_m1-cpu-readings' / 'attempt-summary-011.json').read_bytes())
    original = json.loads((ROOT.parent / '2026-11-04_m1-cpu-readings' / 'attempt-011' / 'completed-result.json').read_bytes())
    declared = json.loads((ROOT / 'downstream-subset-001' / 'declared-input.json').read_bytes())
    completed = json.loads((ROOT / 'downstream-subset-001' / 'completed.json').read_bytes())
    resume_log = ROOT / 'attempt-completed-resume-14-003.log'
    lines = resume_log.read_text().splitlines()
    cli = next(json.loads(line) for line in reversed(lines) if line.startswith('{"project"'))
    assert cli['run_id'] == 14 and cli['status'] == 'complete' and cli['provider'] is None
    assert cli['selected_generation'] is None
    assert cli['output_realization_id'] == original['publication']['realization_id']
    assert cli['release_id'] == original['release_id']
    assert cli['source_realization_id'] == original['report']['realization_id']
    tasks, methods, configs, results, runs, cuts, cut_tasks, batches, realizations, projects = map(table,
        ('ops.task', 'ops.method', 'ops.method_config', 'ops.task_result', 'ops.run',
         'ops.input_cut', 'ops.cut_task', 'data.batch', 'data.realization', 'data.project'))
    origin_result = results.alias('origin_result')
    with open_runtime_engine(Settings(), 'm1-readonly-reuse-verification', purpose='read') as engine:
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn, conn.begin():
            conn.exec_driver_sql('SET TRANSACTION READ ONLY')
            read_only = conn.exec_driver_sql('SHOW transaction_read_only').scalar_one()
            assert read_only == 'on'
            run_rows = {row['id']: dict(row) for row in conn.execute(select(
                runs.c.id, runs.c.project_id, runs.c.release_id, runs.c.input_realization_id,
                runs.c.input_revision, runs.c.dependency_digest, runs.c.sealed, runs.c.status,
                runs.c.result_realization_id).where(runs.c.id.in_((14, 16)))).mappings()}
            query = select(tasks.c.id, tasks.c.run_id, methods.c.name.label('method'),
                tasks.c.unit_type, tasks.c.unit_id, tasks.c.status, tasks.c.attempt,
                tasks.c.reused_task_id, tasks.c.input_hash, tasks.c.packet_hash,
                tasks.c.result_digest, tasks.c.started_at, tasks.c.finished_at,
                configs.c.id.label('config_id'), configs.c.config_hash,
                configs.c.params['subset'].astext.label('subset'),
                sql_json_digest(configs.c.params).label('config_parameters_sha256'),
                sql_json_digest(results.c.body).label('own_output_sha256'),
                func.coalesce(tasks.c.reused_task_id, tasks.c.id).label('effective_origin_task'),
                sql_json_digest(origin_result.c.body).label('effective_output_sha256'))\
                .join(configs, configs.c.id == tasks.c.method_config_id)\
                .join(methods, methods.c.id == configs.c.method_id)\
                .outerjoin(results, results.c.task_id == tasks.c.id)\
                .outerjoin(origin_result, origin_result.c.task_id == func.coalesce(tasks.c.reused_task_id, tasks.c.id))\
                .where(tasks.c.run_id.in_((14, 16))).order_by(tasks.c.run_id, tasks.c.id)
            rows = [dict(row) for row in conn.execute(query).mappings()]
            by_run = {rid: [row for row in rows if row['run_id'] == rid] for rid in (14, 16)}
            views = {rid: [asdict(ref) for ref in selected_source_views(conn, rid)] for rid in (14, 16)}
            cut_rows = [dict(row) for row in conn.execute(select(cuts).where(cuts.c.run_id.in_((14, 16))).order_by(cuts.c.id)).mappings()]
            cut_links = [dict(row) for row in conn.execute(select(cut_tasks).where(
                cut_tasks.c.cut_id.in_((13, 17))).order_by(cut_tasks.c.cut_id, cut_tasks.c.task_id)).mappings()]
            output_ids = [run_rows[rid]['result_realization_id'] for rid in (14, 16)]
            batch_rows = [dict(row) for row in conn.execute(select(batches.c.realization_id,
                batches.c.release_id, batches.c.batch_id, batches.c.content_digest,
                batches.c.data_revision, func.encode(func.sha256(batches.c.content), 'hex').label('stored_content_sha256'))
                .where(batches.c.realization_id.in_(output_ids)).order_by(batches.c.realization_id,batches.c.data_revision)).mappings()]
            realization_rows = [dict(row) for row in conn.execute(select(realizations).where(
                realizations.c.realization_id.in_(output_ids))).mappings()]
            project = dict(conn.execute(select(projects).where(
                projects.c.project_id == run_rows[14]['project_id'])).mappings().one())
            occurrence_counts = {output_id: conn.execute(select(func.count()).select_from(table('data.occurrence')).where(
                table('data.occurrence').c.realization_id == output_id)).scalar_one() for output_id in output_ids}
            # A second query in this read-only snapshot retains exact source/output fingerprints.
            stable_rows = [dict(row) for row in conn.execute(query).mappings()]
    assert stable_rows == rows
    assert all(run_rows[rid]['status'] == 'finished' and run_rows[rid]['sealed'] for rid in (14, 16))
    assert project['selected_result_run_id'] is None and project['generation'] == 0
    assert [view['id'] for view in views[14]] == [22, 23]
    assert views[14] == views[16]
    assert len(by_run[14]) == len(by_run[16]) == 7
    baseline_tasks = {(row['task_id'], row['method'], row['source_view_id'], row['status']) for row in baseline['tasks']}
    assert {(row['id'], row['method'], row['unit_id'], row['status']) for row in by_run[14]} == baseline_tasks
    origins = {(row['method'], row['unit_id']): row for row in by_run[14]}
    comparisons = []
    for row in by_run[16]:
        old = origins[row['method'], row['unit_id']]
        upstream = row['method'] in ('extract.m1_annotations', 'extract.m1_candidates')
        checks = dict(method=row['method'], unit_id=row['unit_id'], original_task=old['id'],
            new_task=row['id'], configuration_same=row['config_id'] == old['config_id'],
            input_same=row['input_hash'] == old['input_hash'],
            declared_origin=row['reused_task_id'], status=row['status'],
            same_effective_output=row['effective_output_sha256'] == old['effective_output_sha256'])
        if upstream:
            assert row['status'] == 'reused' and row['reused_task_id'] == old['id']
            assert checks['configuration_same'] and checks['input_same'] and checks['same_effective_output']
            assert row['own_output_sha256'] is None and old['own_output_sha256'] is not None
        elif row['method'] == 'resolve.m1_readings':
            assert row['subset'] == declared['new_subset'] and old['subset'] == declared['old_subset']
            assert not checks['configuration_same'] and not checks['input_same']
            assert row['status'] in ('done', 'empty') and row['reused_task_id'] is None
        else:
            assert row['method'] == 'ingest.pdf_integrated'
            assert checks['configuration_same'] and not checks['input_same']
            assert row['status'] == 'empty' and row['reused_task_id'] is None
        comparisons.append(checks)
    receipts = {}
    for rid, expected in ((14, original['publication']), (16, completed)):
        actual = next(row for row in batch_rows if row['realization_id'] == expected['realization_id']
                      and row['batch_id'] == expected['receipt']['batch_id'])
        assert actual['content_digest'] == expected['receipt']['content_digest']
        assert actual['data_revision'] == expected['receipt']['data_revision']
        assert actual['stored_content_sha256'] == actual['content_digest']
        assert occurrence_counts[expected['realization_id']] == expected['occurrences']
        final_cut = next(row for row in cut_rows if row['run_id'] == rid and row['final'])
        assert final_cut['id'] == expected['cut_id']
        receipts[str(rid)] = dict(saved=expected, actual_batch=actual, final_cut=final_cut)
    assert {row['id'] for row in cut_rows if row['run_id'] == 14} == {12, 13}
    assert [row['id'] for row in by_run[14]] == [33, 34, 35, 36, 37, 38, 39]
    payload = serial(dict(outcome='passed', at=datetime.now(timezone.utc).isoformat(),
        connection_purpose='read', transaction_read_only=read_only, run14=run_rows[14], run16=run_rows[16],
        declared_change=dict(old_subset=declared['old_subset'], new_subset=declared['new_subset']),
        tasks=rows, comparisons=comparisons, selected_source_views=views, cuts=cut_rows,
        final_cut_origin_links=cut_links, publication_receipts=receipts,
        realizations=realization_rows, occurrence_counts=occurrence_counts, project=project,
        raw_annotation_producer_identity_and_bytes='same referenced immutable origin output; server SHA256 retained',
        completed_resume14=dict(outcome='passed', cli_receipt=cli,
            log_path=resume_log.name, log_sha256=sha256(resume_log.read_bytes()).hexdigest(),
            matches_original_finished_sealed14_cut13=True, same_original_task_ids_and_statuses=True,
            same_original_result_batch_digest_and_revision=True, no_additional_run14_tasks_or_cuts=True,
            source_owner='cli/regenerate.py skips extract_run when result_realization_id exists; finalize_bound_run uses existing final cut; domain_operations._completed_result re-reads immutable receipt',
            historical_limit='No full task-body hash snapshot brackets the historical CLI invocation; current IDs/statuses and original immutable publication receipt match retained baseline. No new CLI execution was performed.'),
        verification_snapshot_unchanged=True,
        limits=['configuration subset reuse only; not fitted parameter quality/benefit',
            'no raw/annotation model execution replayed by this verifier',
            'no same-run source continuation or exact source completion replay claim']))
    OUTPUT.write_bytes(canonical_bytes(payload))
    print(json.dumps(dict(outcome='passed', run16=16, final_cut=17,
        raw_annotation_reuse=[row for row in comparisons if row['method'].startswith('extract.')],
        completed_resume14='passed against retained original receipt and current sealed cut',
        project=project, read_only=read_only)))


if __name__ == '__main__':
    main()
