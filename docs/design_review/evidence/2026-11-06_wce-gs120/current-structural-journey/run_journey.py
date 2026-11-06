"""Phased current GS120 qualification, using exact retained source and normal operations.

`sources` completes/exports all three table-policy arms and artifact diagnostics.
`dossiers` reuses the completed coupled arm and explicit protected structural inputs.
Each phase starts only after the coordinator confirms the deployed source baseline.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from sqlalchemy import text

from corpus_structure.methods.artifact_identity import ArtifactIdentityMethod
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.methods.structural_products import StructuralDossierMethod
from corpus_structure.methods.table_interpretation import POLICY_VERSION
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef, StructuralInput, StructuralPassage,
)
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import (
    ReviewSelection, export_review_bundle, inspect_review_bundle,
)
from corpus_structure.serve.structural_products import (
    DossierRepresentationRequest, StructuralExportRequest, StructuralRequest,
    read_structural_export_page, serve_dossier_representation, serve_structural_products,
)
from corpus_structure.settings import Settings

from journey_support import (
    EVIDENCE, HERE, MODES, PARENT, PROJECT, admit_current, completed_metadata,
    inspect_scoped, retain, run_method, structural_predecessors,
)

POLICIES = ('supported-facet-greedy-1', 'source-order-control-1')


def digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def source_inputs(path):
    packet = json.loads(path.read_bytes())
    coverage = json.loads((path.parent.parent / 'coverage.json').read_bytes())
    if (coverage['outcome'] != 'passed'
        or coverage['native_item_pages'] != list(range(191, 311))
        or coverage['projected_text_pages'] != list(range(191, 311))
        or packet['source_manifest']['parent_sha256'] != PARENT
        or packet['predictions_included']):
        raise ValueError('require exact neutral recovered GS120 source and text coverage')
    inputs = StructuralInput(question='Progressively structure the same GS120 corpus',
        scope='grinstead-snell-physical191-310', inventory_id='gs120-current-source-structure-2',
        policy_id='source-grounded-private-proposals-2',
        sources=tuple(ExternalSourceRef.model_validate(s) for s in packet['sources']),
        passages=tuple(StructuralPassage.model_validate(p) for p in packet['passages']),
        dependencies=('source-packet:' + sha256(path.read_bytes()).hexdigest(),),
        coverage_limits=('Native geometry, model readings and factor results remain unassessed proposals.',
            'Missing dossier sections remain gaps; inventory counts do not establish capture recall.'))
    if len(inputs.sources) != 48:
        raise ValueError('current GS120 journey requires the exact48 recovered nonempty source views')
    return inputs, coverage


def prepared_release(settings, output, release_id):
    if release_id:
        with open_runtime_engine(settings, 'gs120-current-existing-release', purpose='read') as engine:
            with read_snapshot(engine) as conn:
                prepared = load_release(conn, release_id)
        retain(output / 'release.json', dict(release_id=prepared.release_id,
            acquisition='exact already admitted current release'))
        return prepared
    return admit_current(settings, output)


def annotation_requests(inputs):
    return tuple(ContributionRequest(run_id=s.run_id, source_view_id=s.source_view_id,
        method='extract.m1_annotations', max_bytes=128_000_000) for s in inputs.sources)


def scoped_requests(run, inputs):
    return tuple(ContributionRequest(run_id=run['run_id'], source_view_id=s.source_view_id,
        method=ScopedRelationsMethod.name, include_interpretation=True,
        limit=1000, page_bytes=16_000_000, max_bytes=128_000_000) for s in inputs.sources)


def portable(selection, destination, settings):
    if destination.exists():
        inspection = inspect_review_bundle(destination)
        manifest = json.loads((destination / 'manifest.json').read_bytes())
        if manifest['selection'] != selection.model_dump(mode='json'):
            raise ValueError('retained portable selection differs from current exact phase')
    else:
        manifest = export_review_bundle(selection, destination, settings)
        inspection = inspect_review_bundle(destination)
    retain(destination.with_suffix('.json'), dict(manifest=manifest, detached=inspection))
    return manifest


def population_control(bundle, run, inputs, destination):
    """Read the verified detached raw producer once; preserve all policy outcomes."""
    candidate_rows, contribution_ids, outcomes, policies = [], set(), Counter(), set()
    categories, executed_modes, coupling = Counter(), Counter(), Counter()
    sources = set()
    with (bundle / 'reports.jsonl').open('rb') as stream:
        for line in stream:
            raw = json.loads(json.loads(line)['payload_json'])
            body = raw.get('body') or {}
            if body.get('method') != ScopedRelationsMethod.name:
                continue
            sources.add(raw['origin_unit_id'])
            contribution_ids.update(c['contribution_id'] for c in body.get('contributions', ()))
            for operation in body.get('contribution_operations', ()):
                report = operation.get('local_interpretation')
                if report is None:
                    continue
                outcomes[report['outcome']] += 1
                request = source_python(report['request']) if 'request' in report else None
                if report['policy_version'] == POLICY_VERSION:
                    policies.add(report['policy_version'])
                    category = 'actual_v2_request' if request is not None else 'unavailable_v2_band'
                    if request is None and report['outcome'] != 'not_run':
                        raise ValueError('v2 band lacks request without declaring not_run')
                elif (operation['question'] == 'table attachment interpretation'
                    and report['policy_version'] == 'table-interpretation-1'
                    and report['outcome'] == 'not_run' and report['policy_mode'] == 'not_run'
                    and report['probability_standing'] == 'not_computed'
                    and not report['coupling_enabled'] and request is None and 'result' not in report):
                    category = 'no_applicable_band_generic_retention'
                else:
                    raise ValueError('unexpected policy or mathematical claim in current source arm')
                categories[category] += 1
                if request is not None:
                    executed_modes[report['policy_mode']] += 1
                    coupling[str(report['coupling_enabled'])] += 1
                decisions = None if request is None else sorted((dict(key=d['key'],
                    candidates=sorted(c['key'] for c in d['candidates']))
                    for d in request['decisions']), key=lambda d: d['key'])
                candidate_rows.append(dict(operation_key=operation['operation_key'], category=category,
                    contribution_ids=sorted(report['contribution_ids']), decisions=decisions))
    if (sources != {s.source_view_id for s in inputs.sources} or policies != {POLICY_VERSION}
        or categories['actual_v2_request'] == 0 or outcomes['completed'] == 0):
        raise ValueError('portable source/policy closure differs from current48-view v2 arm')
    candidate_rows.sort(key=lambda row: row['operation_key'])
    result = dict(run=run, sources=sorted(sources), contributions=len(contribution_ids),
        contribution_ids_digest=digest(sorted(contribution_ids)),
        candidate_universe_digest=digest(candidate_rows), candidate_questions=len(candidate_rows),
        policy_versions=sorted(policies), outcomes=dict(outcomes), case_categories=dict(categories),
        executed_policy_modes=dict(executed_modes), coupling_enabled_counts=dict(coupling),
        standing='private candidate-relative mathematical diagnostics; no independent support')
    retain(destination / 'candidate-universe.json', candidate_rows)
    retain(destination / 'population-control.json', result)
    return result


def inspect_artifact(settings, run, output):
    request = StructuralExportRequest(run_id=run['run_id'], cut_id=run['cut_id'],
        kind='artifact_identity', max_bytes=128_000_000)
    if (output / 'inspection.json').exists():
        return request, json.loads((output / 'inspection.json').read_bytes())
    with open_runtime_engine(settings, 'gs120-artifact-reader', purpose='read') as engine:
        with read_snapshot(engine) as conn:
            page = read_structural_export_page(conn, request)
            if len(page.reports) != 1:
                raise ValueError('artifact file selection must contain one exact actual RUN report')
            retain(output / 'file-page.json', page.model_dump(mode='json'))
            # The ordinary interactive route is exercised under its unchanged8M cap.
            interactive = serve_structural_products(conn, StructuralRequest(
                run_id=run['run_id'], cut_id=run['cut_id'], kind='artifact_identity', max_bytes=8_000_000))
            retain(output / 'interactive-page.json', interactive.model_dump(mode='json'))
    product = page.reports[0].artifact_identity
    result = dict(outcome='passed', product_id=page.reports[0].product_id,
        records=len(product.records), pairs=len(product.pairs), native_alias_pairs=len(product.native_alias_pairs),
        unbound_sources=product.unbound_source_ids, identity_grain=product.identity_grain,
        policy=product.policy.model_dump(mode='json'), standing=product.standing,
        probabilities='declared diagnostic assumptions, not fitted/calibrated truth')
    retain(output / 'inspection.json', result)
    return request, result


def sources_phase(settings, prepared, inputs, output, attempt):
    if POLICY_VERSION != 'shared-table-band-2':
        raise ValueError('new source qualification requires the corrected table-policyv2')
    bindings = [dict(native_content_digest=d, source_work=PARENT,
        provenance='Authenticated GS120 recovered native-parent-map and original parent SHA256')
        for d in sorted({s.native_content_digest for s in inputs.sources})]
    arms, controls = [], []
    for mode in MODES:
        root = output / ('scoped-' + mode)
        run = run_method(settings, prepared, ScopedRelationsMethod(), dict(inputs=inputs.model_dump(mode='json'),
            structural_input_digest=inputs.identity, work_bindings=bindings, interpretation_mode=mode),
            inputs, root, 'v2-scoped-' + mode, attempt)
        refs, requests = inspect_scoped(settings, run, inputs, root)
        selection = ReviewSelection(selections=(*requests, *annotation_requests(inputs)),
            max_bytes=512_000_000 if mode == 'coupled' else 256_000_000)
        bundle = output / ('review-' + mode)
        portable(selection, bundle, settings)
        control = population_control(bundle, run, inputs, root)
        controls.append(control)
        arms.append(dict(mode=mode, run=run, contribution_predecessors=len(refs), control=control))
    if len({c['contribution_ids_digest'] for c in controls}) != 1 or len({c['candidate_universe_digest'] for c in controls}) != 1:
        raise ValueError('three policy arms did not operate on identical actual contributions/candidate universes')
    retain(output / 'matched-populations.json', dict(outcome='passed', arms=controls,
        scope='Same48sources, exact same contribution IDs and candidate choices; outcomes remain arm-specific'))
    artifact_root = output / 'artifact'
    policy = json.loads((HERE / 'artifact-policy.json').read_bytes())
    artifact = run_method(settings, prepared, ArtifactIdentityMethod(), dict(inputs=inputs.model_dump(mode='json'),
        structural_input_digest=inputs.identity, work_bindings=bindings, policy=policy),
        inputs, artifact_root, 'v2-artifact', attempt)
    request, summary = inspect_artifact(settings, artifact, artifact_root)
    portable(ReviewSelection(structural_selections=(request,), max_bytes=256_000_000),
        output / 'review-artifact', settings)
    result = dict(outcome='passed', phase='sources', policy_version=POLICY_VERSION,
        arms=arms, artifact=artifact, artifact_inspection=summary,
        sources=len(inputs.sources), physical_pages=list(range(191, 311)), semantic_quality='unassessed',
        scope='Actual native completion, identical candidate populations, ordinary bounded Reader and full portable file closure')
    retain(output / 'result.json', result)
    return result


def dossier_task_id(conn, run):
    rows = conn.execute(text(
        'SELECT task.id FROM ops.cut_task member JOIN ops.task task ON task.id=member.task_id '
        'JOIN ops.method_config config ON config.id=task.method_config_id '
        'JOIN ops.method method ON method.id=config.method_id '
        "WHERE member.cut_id=:cut AND task.unit_type='run' AND method.name='structure.dossier'"
    ), dict(cut=run['cut_id'])).scalars().all()
    if len(rows) != 1:
        raise ValueError('completed dossier cut must select exactly one RUN task')
    return rows[0]


def inspect_dossier(settings, run, output):
    request = StructuralExportRequest(run_id=run['run_id'], cut_id=run['cut_id'],
        kind='dossier', max_bytes=128_000_000)
    if (output / 'inspection.json').exists():
        return request, json.loads((output / 'inspection.json').read_bytes())
    with open_runtime_engine(settings, 'gs120-dossier-pages-and-files', purpose='read') as engine:
        with read_snapshot(engine) as conn:
            task_id = dossier_task_id(conn, run)
            selected = DossierRepresentationRequest(run_id=run['run_id'], cut_id=run['cut_id'],
                task_id=task_id, limit=2, max_bytes=8_000_000)
            pages, selected_ids = [], []
            while True:
                page = serve_dossier_representation(conn, selected)
                pages.append(page.model_dump(mode='json'))
                selected_ids.extend(m['member_id'] for m in page.members)
                if page.continuation is None:
                    break
                selected = selected.model_copy(update=dict(continuation=page.continuation))
            retain(output / 'representative-pages.json', pages)
            full = read_structural_export_page(conn, request)
            if len(full.reports) != 1:
                raise ValueError('dossier file selection must retain one complete original product')
            retain(output / 'full-file-page.json', full.model_dump(mode='json'))
    report = full.reports[0]
    dossier = report.dossier
    if tuple(selected_ids) != dossier.representatives or any(
        p['full_member_count'] != len(dossier.members)
        or p['membership_digest'] != dossier.representation.membership_digest
        or p['facet_digest'] != dossier.representation.facet_digest for p in pages):
        raise ValueError('bounded representation differs from complete file membership/facets')
    result = dict(outcome='passed', product_id=report.product_id, task_id=task_id,
        policy=dossier.representation.policy, member_budget=dossier.representation.member_budget,
        full_member_count=len(dossier.members), selected=len(dossier.representatives),
        omitted=len(dossier.representation.omitted), supported_facets=len(dossier.supported_facets),
        represented_facets=len(dossier.representation.represented_facets),
        missing_facets=len(dossier.representation.missing_facets), missing_sections=dossier.missing_sections,
        mandatory_overflow=dossier.representation.mandatory_overflow, pages=len(pages),
        membership_digest=dossier.representation.membership_digest, facet_digest=dossier.representation.facet_digest,
        native_file_bytes=len(canonical_bytes(full.model_dump(mode='json'))),
        scope='Full membership retained; bounded interactive pages and full-file port compared exactly')
    retain(output / 'inspection.json', result)
    return request, result


def dossiers_phase(settings, prepared, inputs, output, attempt, sources_root, structural_runs):
    source_phase = json.loads((sources_root / 'phase.json').read_bytes())
    if (source_phase['phase'] != 'sources'
        or source_phase['protocol'] != 'gs120-current-structural-journey-2'
        or source_phase['table_policy_version'] != POLICY_VERSION):
        raise ValueError('dossiers require the current v2 source-arm target')
    if json.loads((sources_root / 'inputs.json').read_bytes()) != inputs.model_dump(mode='json'):
        raise ValueError('dossier input closure differs from exact source-arm closure')
    coupled = json.loads((sources_root / 'scoped-coupled/completed.json').read_bytes())
    control = json.loads((sources_root / 'scoped-coupled/population-control.json').read_bytes())
    portable_receipt = json.loads((sources_root / 'review-coupled.json').read_bytes())
    if (control['run'] != coupled or control['policy_versions'] != [POLICY_VERSION]
        or not control['case_categories']['actual_v2_request'] or not control['outcomes']['completed']
        or not portable_receipt['detached']):
        raise ValueError('coupled source arm lacks completed native/verified portable evidence')
    refs = tuple(RetainedContributionRef.model_validate(r) for r in json.loads(
        (sources_root / 'scoped-coupled/contribution-predecessors.json').read_bytes()))
    if (digest(sorted(r.contribution_id for r in refs)) != control['contribution_ids_digest']
        or any(r.run_id != coupled['run_id'] or r.cut_id != coupled['cut_id'] for r in refs)):
        raise ValueError('dossier contribution references differ from exact coupled population')
    predecessors, predecessor_requests = structural_predecessors(settings, structural_runs, inputs, output)
    predecessor_selection = json.loads((output / 'structural-predecessor-selection.json').read_bytes())
    if not predecessors or not sum(p['published_structural_assertions'] for p in predecessor_selection['public_assertions']):
        raise ValueError('dossiers require explicit current protected positive structural predecessor assertions')
    dossier_inputs = inputs.model_copy(update=dict(dependencies=(
        *inputs.dependencies, *(r.contribution_id for r in refs), *(r.product_id for r in predecessors))))
    summaries = []
    exports = []
    for policy in POLICIES:
        root = output / ('dossier-' + policy)
        run = run_method(settings, prepared, StructuralDossierMethod(), dict(inputs=dossier_inputs.model_dump(mode='json'),
            structural_input_digest=dossier_inputs.identity, root_id='gs120-corpus-structure',
            predecessors=[r.model_dump(mode='json') for r in predecessors],
            contribution_predecessors=[r.model_dump(mode='json') for r in refs], member_budget=12, policy=policy),
            dossier_inputs, root, 'v2-dossier-' + policy, attempt)
        request, summary = inspect_dossier(settings, run, root)
        selection = ReviewSelection(selections=(*scoped_requests(coupled, inputs), *annotation_requests(inputs)),
            structural_selections=(*predecessor_requests, request), max_bytes=512_000_000)
        exports.append((selection, output / ('review-' + policy)))
        summaries.append(dict(run=run, inspection=summary))
    before, after = (item['inspection'] for item in summaries)
    if (before['membership_digest'] != after['membership_digest'] or before['facet_digest'] != after['facet_digest']
        or before['full_member_count'] != after['full_member_count'] or before['member_budget'] != after['member_budget']):
        raise ValueError('equal-budget dossier policies changed full membership or supported facet population')
    if not before['supported_facets'] or not after['supported_facets']:
        raise ValueError('positive independently supported structural facets missing from actual protected predecessor')
    # Native completion and bounded/full-file inspection precede expensive portable closure.
    for selection, destination in exports:
        portable(selection, destination, settings)
    result = dict(outcome='passed', phase='dossiers', sources_phase=str(sources_root),
        coupled_source_run=coupled, structural_predecessors=[r.model_dump(mode='json') for r in predecessors],
        policies=summaries, full_membership_equal=True, supported_facet_population_equal=True,
        semantic_quality='source contributions remain proposed; only exact protected structural assessments supply support',
        scope='Two actual equal-budget policies over identical full membership; no display omission deletes knowledge')
    retain(output / 'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('sources', 'dossiers'))
    parser.add_argument('attempt')
    parser.add_argument('--release-id')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--source-packet', type=Path, default=EVIDENCE / 'source-recovery/attempt001/source-packets/source-packet.json')
    parser.add_argument('--sources-attempt', type=Path)
    parser.add_argument('--structural-run', type=int, action='append', default=[])
    args = parser.parse_args()
    if args.phase == 'dossiers' and (args.sources_attempt is None or not args.structural_run):
        parser.error('dossiers requires --sources-attempt and explicit --structural-run')
    output = HERE / (args.phase + args.attempt)
    existed = output.exists()
    output.mkdir(exist_ok=args.resume)
    if existed and not (output / 'phase.json').exists():
        raise ValueError('existing directory is not a current phased journey; no v1 stage promotion')
    try:
        inputs, coverage = source_inputs(args.source_packet)
        retain(output / 'phase.json', dict(protocol='gs120-current-structural-journey-2', phase=args.phase,
            table_policy_version=POLICY_VERSION, source_packet_sha256=sha256(args.source_packet.read_bytes()).hexdigest(),
            structural_runs=args.structural_run, sources_attempt=str(args.sources_attempt) if args.sources_attempt else None))
        retain(output / 'inputs.json', inputs.model_dump(mode='json'))
        retain(output / 'source-coverage.json', coverage)
        settings = Settings()
        prepared = prepared_release(settings, output, args.release_id)
        if args.phase == 'sources':
            result = sources_phase(settings, prepared, inputs, output, args.attempt)
        else:
            result = dossiers_phase(settings, prepared, inputs, output, args.attempt,
                args.sources_attempt, args.structural_run)
        print(json.dumps(result), flush=True)
    except BaseException as error:
        failure = output / 'failure.json'
        number = 1
        while failure.exists():
            failure = output / ('failure-resume-' + str(number) + '.json')
            number += 1
        retain(failure, dict(outcome='interrupted' if isinstance(error, KeyboardInterrupt) else 'failed',
            type=type(error).__name__, message=str(error)))
        raise


if __name__ == '__main__':
    main()
