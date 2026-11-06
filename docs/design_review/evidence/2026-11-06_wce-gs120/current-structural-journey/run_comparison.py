"""Compare two authentic event predicates through the registered source-bound route.

Run after coordinator readiness and the sources phase. The ordinary parser must
retain unknown units and withhold numerical interval or rule-authority claims.
"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.methods.structural_products import StructuralComparisonMethod
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import ExternalSourceRef, StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection, prepare_structural_sources,
)
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import (
    StructuralExportRequest, StructuralRequest, read_structural_export_page, serve_structural_products,
)
from corpus_structure.settings import Settings

from journey_support import EVIDENCE, HERE, retain, run_method
from run_journey import portable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    parser.add_argument('--release-id', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    output = HERE / ('comparison' + args.attempt)
    output.mkdir(exist_ok=args.resume)
    try:
        packet_path = EVIDENCE / 'source-recovery/attempt001/source-packets/source-packet.json'
        packet = json.loads(packet_path.read_bytes())
        investigation = json.loads((HERE / 'comparison-investigation.json').read_bytes())
        selected = investigation['proposed_comparison']
        if sha256(packet_path.read_bytes()).hexdigest() != investigation['source_packet_sha256']:
            raise ValueError('comparison investigation no longer binds exact source packet')
        source = next(ExternalSourceRef.model_validate(row) for row in packet['sources']
            if ExternalSourceRef.model_validate(row).identity == selected['source_ref'])
        original = next(p for p in packet['passages'] if p['passage_id'] == selected['original_passage_id'])
        selections = []
        for name in ('left', 'right', 'context'):
            span = selected[name]
            if original['text'][span['start']:span['end']] != span['text']:
                raise ValueError('comparison selected text differs from retained source')
            selections.append(StructuralPassageSelection(run_id=source.run_id,
                source_view_id=source.source_view_id, passage_id='gs120-exercise7-' + name,
                start=original['start'] + span['start'], end=original['start'] + span['end'],
                scope=original['scope']))
        settings = Settings()
        with open_runtime_engine(settings, 'gs120-comparison-source-preparation', purpose='read') as engine:
            with read_snapshot(engine) as conn:
                prepared = load_release(conn, args.release_id)
            frozen = prepare_structural_sources(engine, tuple(selections))
        inputs = StructuralInput(question='Source-grounded comparison of two event predicates',
            scope=original['scope'], inventory_id='gs120-same-exercise-thresholds-1',
            policy_id='literal-threshold-fields-no-invented-unit-1', sources=frozen.sources,
            passages=frozen.passages, dependencies=('source-packet:' + investigation['source_packet_sha256'],),
            coverage_limits=tuple(selected['scope_limits']))
        retain(output / 'inputs.json', inputs.model_dump(mode='json'))
        run = run_method(settings, prepared, StructuralComparisonMethod(), dict(
            inputs=inputs.model_dump(mode='json'), structural_input_digest=inputs.identity,
            left_id='gs120-exercise7-left', right_id='gs120-exercise7-right'),
            inputs, output / 'native', 'actual-source-comparison', args.attempt)
        request = StructuralExportRequest(run_id=run['run_id'], cut_id=run['cut_id'],
            kind='qualified_comparison', max_bytes=128_000_000)
        with open_runtime_engine(settings, 'gs120-comparison-inspection', purpose='read') as engine:
            with read_snapshot(engine) as conn:
                interactive = serve_structural_products(conn, StructuralRequest(
                    run_id=run['run_id'], cut_id=run['cut_id'], kind='qualified_comparison', max_bytes=8_000_000))
                file_page = read_structural_export_page(conn, request)
        retain(output / 'interactive-page.json', interactive.model_dump(mode='json'))
        retain(output / 'file-page.json', file_page.model_dump(mode='json'))
        if len(file_page.reports) != 1:
            raise ValueError('expected exactly one actual current comparison report')
        comparison = file_page.reports[0].comparison
        threshold = next(d for d in comparison.dimensions if d.dimension == 'threshold_unit')
        if (threshold.left.typed.quantity, threshold.left.typed.comparator, threshold.left.typed.value,
            threshold.right.typed.quantity, threshold.right.typed.comparator, threshold.right.typed.value) != ('T', '>', '3', 'T', '>', '6'):
            raise ValueError('source comparison failed to retain literal event predicate fields')
        if threshold.left.typed.unit is not None or threshold.right.typed.unit is not None or threshold.typed_outcome != 'unknown' or threshold.removed_interval is not None or threshold.added_interval is not None:
            raise ValueError('comparison invented a unit or stronger numerical consequence')
        portable(ReviewSelection(structural_selections=(request,), max_bytes=256_000_000),
            output / 'portable', settings)
        retain(output / 'result.json', dict(outcome='passed', run=run,
            product_id=file_page.reports[0].product_id, lexical_outcome=threshold.outcome,
            typed_outcome=threshold.typed_outcome, applicability=comparison.applicability,
            interval_consequence='withheld; explicit unit absent',
            source_scope='Two event predicates in the same retained die-roll exercise, not rule revisions',
            scope='Actual registered native replay, ordinary Reader and portable source closure; private proposal only'))
    except BaseException as error:
        target = output / 'failure.json'
        index = 1
        while target.exists():
            target = output / ('failure-resume-' + str(index) + '.json')
            index += 1
        retain(target, dict(outcome='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
            type=type(error).__name__, message=str(error)))
        raise


if __name__ == '__main__':
    main()
