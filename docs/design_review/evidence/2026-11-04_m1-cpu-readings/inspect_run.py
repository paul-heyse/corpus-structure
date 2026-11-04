"""Summarize actual sealed source reports; no reference/quality inference."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main():
    run_id = int(sys.argv[1])
    output = Path(sys.argv[2])
    task, result, config, method, runs = map(table, (
        'ops.task', 'ops.task_result', 'ops.method_config', 'ops.method', 'ops.run'))
    reports = []
    with open_runtime_engine(Settings(), 'm1-actual-source-summary', purpose='read') as engine, engine.connect() as conn:
        run = dict(conn.execute(select(runs).where(runs.c.id == run_id)).mappings().one())
        query = (select(task.c.id, task.c.status, task.c.unit_id, method.c.name, result.c.body)
            .join(config, config.c.id == task.c.method_config_id)
            .join(method, method.c.id == config.c.method_id)
            .outerjoin(result, result.c.task_id == task.c.id)
            .where(task.c.run_id == run_id).order_by(task.c.id))
        for row in conn.execute(query).mappings():
            body = row['body'] or {}
            detail = source_python(body['parse_detail']) if body.get('parse_detail') else {}
            native = [value['report'] for value in detail.get('reports', ()) if 'report' in value]
            diagnostics = Counter(d.get('code', d.get('reason', 'unknown'))
                for report in detail.get('reports', ()) for d in report.get('diagnostics', ()))
            groups = Counter()
            for report in native:
                for family, values in json.loads(report['raw_json']).items():
                    if isinstance(values, list):
                        groups[family] += len(values)
            reports.append(dict(task_id=row['id'], method=row['name'], status=row['status'],
                source_view_id=row['unit_id'], records=dict(Counter(r['family'] for r in body.get('records', ()))),
                contexts=len(detail.get('contexts', ())), regions=len(detail.get('regions', ())),
                execution=dict(Counter(f"{x['family']}:{x['outcome']}" for x in detail.get('execution', ()))),
                assembly_diagnostics=dict(diagnostics), raw_groups=dict(groups), native_calls=len(native),
                resident_cold_calls=sum(not r['resident_reused'] for r in native),
                native_inference_seconds=sum(r['inference_seconds'] for r in native),
                max_input_bytes=max((r['preparation']['input_bytes'] for r in native), default=0),
                max_subwords=max((r['preparation']['subwords'] for r in native), default=0)))
    payload = dict(run_id=run_id, release_id=run['release_id'], run_status=run['status'],
        sealed=run['sealed'], scope='actual_cpu_source_reports_only',
        quality_claim='not_established', tasks=reports)
    with output.open('xb') as stream:
        stream.write(canonical_bytes(payload))
    print(json.dumps(payload))


if __name__ == '__main__':
    main()
