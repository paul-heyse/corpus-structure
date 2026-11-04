"""Run explicit NONDEFAULT M1 custody/readings on retained integrated products."""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.commands import start_bound_run
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.authored_sql import (
    admit_archived_sql, analyze_archived_sql, has_authored_sql,
)
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ORIGINS = ('grinstead-snell', 'forbes-statistical-distributions', 'nist-ehandbook')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origin', choices=(*ORIGINS, 'all'))
    parser.add_argument('output_name')
    parser.add_argument('configuration', nargs='?', default='readings',
                        choices=('source-only', 'default', 'described', 'readings', 'contextual'))
    parser.add_argument('--record-policy', type=Path)
    parser.add_argument('--publish', action='store_true',
                        help='Finish a NONDEFAULT result; source-only always finishes its source snapshot.')
    args = parser.parse_args()
    out = HERE / args.output_name
    out.mkdir(exist_ok=False)
    (out / 'executed-runner.py.txt').write_bytes(Path(__file__).read_bytes())
    policy = json.loads(args.record_policy.read_bytes()) if args.record_policy else None
    settings = Settings()
    bundle, deps, profile, prepared = prepare_pack(Path('domains/statistics'))
    with open_runtime_engine(settings, 'm1-reading-release', purpose='admit') as engine, engine.begin() as conn:
        persist_release(conn, bundle, deps, profile, prepared)
    with open_runtime_engine(settings, 'm1-reading-admit', purpose='admit') as engine, engine.begin() as conn:
        if has_authored_sql(prepared):
            with open_runtime_engine(settings, 'm1-reading-sql', purpose='read') as reader_engine, reader_engine.connect() as reader:
                analyzed = analyze_archived_sql(reader, prepared.release_id)
            admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
        admit_release(prepared, connection=conn)
    method_settings = MethodSettings(data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache)
    results = []
    for origin in ORIGINS if args.origin == 'all' else (args.origin,):
        target = out / origin if args.origin == 'all' else out
        target.mkdir(exist_ok=True)
        source = json.loads((HERE.parent / '2026-11-04_m1-source-populations/intake001' / origin / 'result.json').read_bytes())
        pin = source['source_freeze']['pins'][0]['native_product']
        project = 'm1-source-' + origin
        realization = 'm1-reading-input:' + origin + ':' + prepared.release_id
        with open_runtime_engine(settings, 'm1-cpu-readings', purpose='write') as engine:
            with engine.begin() as conn:
                initialize_source_project(conn, project_id=ProjectId(project),
                    release_id=ReleaseId(prepared.release_id), realization_id=RealizationId(realization),
                    projection_context=prepared)
            started = perf_counter()
            report = start_bound_run(engine, release_id=prepared.release_id, realization_id=realization,
                project_id=project, domain='statistics', method_settings=method_settings,
                extraction_policy='m1-candidate', m1_configuration=args.configuration,
                record_policy=policy, integrated_product=ProductReference(
                    pin['task_id'], pin['product_key'], pin['content_digest']))
            result = dict(report=report.model_dump(mode='json'), seconds=perf_counter() - started,
                release_id=prepared.release_id, origin_group=origin, project_id=project,
                configuration=args.configuration, native_product=pin,
                execution_scope='source_custody_only' if args.configuration == 'source-only' else 'cpu_source_readings')
            (target / 'source-run.json').write_bytes(canonical_bytes(result))
            if args.publish or args.configuration == 'source-only':
                with engine.begin() as conn:
                    cut = seal_cut(conn, report.run_id, 'm1-explicit-final', final=True)
                published = consolidate_cut(engine, cut, 'm1-result:' + str(report.run_id) + ':' + prepared.release_id)
                result['publication'] = asdict(published)
                result['source_run_id'], result['source_cut_id'] = int(report.run_id), int(cut)
                (target / 'completed-result.json').write_bytes(canonical_bytes(result))
            results.append(result)
            print(json.dumps(dict(outcome='passed', **result)), flush=True)
    (out / 'results.json').write_bytes(canonical_bytes(dict(release_id=prepared.release_id, results=results)))


if __name__ == '__main__':
    main()
