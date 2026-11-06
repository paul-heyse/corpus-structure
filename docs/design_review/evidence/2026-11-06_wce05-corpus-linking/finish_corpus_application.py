"""Refresh normal deployment admission, finalize and export an already completed app task.

No source/provider/linking/applicability operation is executed again.
"""

import argparse
from pathlib import Path

from sqlalchemy import select

from corpus_native_journey import metadata, save
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.review_bundle import ReviewSelection, export_review_bundle, verify_review_bundle
from corpus_structure.serve.structural_products import StructuralRequest, serve_structural_products
from corpus_structure.settings import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    parser.add_argument('--run', type=int, required=True)
    args = parser.parse_args()
    output = Path(__file__).resolve().parent / args.attempt
    output.mkdir(exist_ok=False)
    settings = Settings()
    try:
        with open_runtime_engine(settings, 'wce05-finish-release', purpose='read') as engine, read_snapshot(engine) as conn:
            release_id = conn.scalar(select(table('ops.run').c.release_id).where(table('ops.run').c.id == args.run))
            prepared = open_release(conn, release_id)
            tasks, results = table('ops.task'), table('ops.task_result')
            native = conn.execute(select(results.c.body).join(tasks, tasks.c.id == results.c.task_id).where(tasks.c.run_id == args.run)).scalars().all()
            save(output, 'completed-native-task-results.json', native)
        # A managed native migration changes deployment admission, not release meaning.
        # Only the restricted admission purpose can refresh this existing release receipt.
        with open_runtime_engine(settings, 'wce05-finish-admit', purpose='admit') as engine, engine.begin() as conn:
            admit_release(prepared, connection=conn)
        with open_runtime_engine(settings, 'wce05-finish-app', purpose='write') as engine:
            finalize_bound_run(engine, args.run, 'wce05-applicability-result:' + str(args.run))
        request = StructuralRequest(run_id=args.run, kind='definition_applicability')
        with open_runtime_engine(settings, 'wce05-finish-read', purpose='read') as engine, read_snapshot(engine) as conn:
            page = serve_structural_products(conn, request)
            completed, revision, runtime = metadata(conn, args.run)
            save(output, 'applicability-inspection.json', page.model_dump(mode='json'))
        exported = export_review_bundle(ReviewSelection(structural_selections=(request,)), output / 'applicability-bundle', settings)
        verified = verify_review_bundle(output / 'applicability-bundle')
        save(output, 'applicability-export.json', exported)
        save(output, 'applicability-export-verification.json', verified)
        readings = [reading for report in page.reports for reading in report.definition.readings]
        save(output, 'result.json', dict(outcome='passed', run_id=args.run, cut_id=completed['cut_id'], release_id=release_id,
            result_revision=revision, runtime_fingerprint=runtime, applicability_outcomes=[r.outcome for r in readings],
            premises=[p.model_dump(mode='json') for r in readings for p in r.premises],
            provider_execution='not_run: reuse completed source/provider/relationship127 and native applicability130',
            scope='actual native private applicability retention, ordinary read and verified portable export',
            independent_assessment='not_run', public_admission='not_run'))
    except BaseException as error:
        save(output, 'failure.json', dict(outcome='failed', error_type=type(error).__name__, reason=str(error)))
        raise


if __name__ == '__main__':
    main()
