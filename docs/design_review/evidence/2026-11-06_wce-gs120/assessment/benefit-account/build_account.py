"""Assemble existing independent evidence without a production or database oracle."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATHS = {
    'baseline_product': 'baseline003-export001/structural-inspection.json',
    'baseline_A': 'authors/output-definition-review/a/review.json',
    'baseline_B': 'authors/output-definition-review/b/assessment.json',
    'baseline_C': 'authors/output-definition-review/c/adjudicated-assessment.json',
    'baseline_C_receipt': 'authors/output-definition-review/c/literal-validation-receipt.json',
    'current_product': 'current-extraction/named001/structural-inspection.json',
    'current_A': 'authors/current-named-review/a/assessment.json',
    'current_B': 'authors/current-named-review/b/assessment.json',
    'current_C': 'authors/current-named-review/c/assessment.json',
    'current_A_receipt': 'authors/current-named-review/a/receipt.json',
    'current_B_receipt': 'authors/current-named-review/b/validation-receipt.json',
    'current_C_receipt': 'authors/current-named-review/c/validation-receipt.json',
    'common_A': 'authors/common-review/a/review.json',
    'common_B': 'authors/common-review/b/review.json',
    'common_C': 'authors/c/source-adjudication/adjudicated-source-cases.json',
    'common_C_receipt': 'authors/c/source-adjudication/literal-validation-receipt.json',
    'extra_C': 'authors/c/source-recovery-assessment/source-cases.json',
    'extra_C_receipt': 'authors/c/source-recovery-assessment/literal-validation-receipt.json',
    'source_inventory_812': 'assessment/source-complete001/source-summary.json',
    'recovery_coverage': 'source-recovery/attempt001/coverage.json',
    'final_source_capture': 'assessment/final-source-capture/source-capture-assessment.json',
    'final_source_capture_receipt': 'assessment/final-source-capture/validation-receipt.json',
    'final_named_transport': 'assessment/run160-exact-transport001.json',
    'protected_reference': 'assessment/protected-current/native160/protected-reference-receipt.json',
    'protected_publication': 'assessment/protected-current/native160/final-verification.json',
    'contextual_assessment': 'assessment/final-source-capture/contextual-attachment-assessment.json',
    'policy_assessment': 'assessment/final-source-capture/policy-band-assessment.json',
    'table_note_assessment': 'assessment/final-source-capture/table-note-assessment.json',
    'artifact_assessment': 'assessment/final-source-capture/artifact-occurrence-assessment.json',
    'artifact_link_assessment': 'assessment/final-source-capture/artifact-link-assessment.json',
    'downstream_failures': 'assessment/final-source-capture/downstream-failure-account.json',
    'comparison': 'current-structural-journey/comparison001/result.json',
    'model_C': 'assessment/final-source-capture/model161-assessment.json',
    'model_C_receipt': 'assessment/final-source-capture/model161-validation-receipt.json',
    'model_provider_inventory': 'assessment/final-source-capture/model161-provider-inventory.json',
    'model_manifest': 'assessment/run161-final-model001/manifest.json',
    'model_checkpoint': 'gliner25-current161-verification.json',
    'model_cli': 'consumer-transports/model161-cli.json',
    'published_mcp': 'consumer-transports/published169-mcp001/result.json',
}


def read(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def citation(path, pointer):
    return {'path': path, 'sha256': sha(path), 'json_pointer': pointer}


def packet_inventory(prefix):
    packets = {}
    views = {}
    for file in sorted((ROOT / prefix).glob('grinstead*.json')):
        path = str(file.relative_to(ROOT))
        packet = read(path)
        packets[path] = packet
        for index, view in enumerate(packet['views']):
            views[view['passage']['passage_id']] = (path, packet, index, view)
    return packets, views


def pages(packet, view, selected):
    mapping = {x['excerpt_physical_page']: x['parent_physical_page'] for x in packet['page_map']}
    items = {x['self_ref']: x for x in view['native_context']['items']}
    chosen = [items[x['item_ref']] for x in view['native_context']['pieces'] if x.get('item_ref')] if selected else items.values()
    return {mapping[p['page_no']] for item in chosen for p in item.get('prov', [])}


def endpoint_identity(endpoint, views):
    _, _, _, view = views[endpoint['passage_id']]
    p = view['native_view']
    segments = []
    for piece in view['native_context']['pieces']:
        if piece.get('item_ref') and piece['start'] < endpoint['end'] and piece['end'] > endpoint['start']:
            s, e = max(endpoint['start'], piece['start']), min(endpoint['end'], piece['end'])
            segments.append([piece['item_ref'], piece['source_field'], piece.get('cell_index'), s-piece['start'], e-piece['start'], view['passage']['text'][s:e]])
    return {'native_task_id': p['native_task_id'], 'native_product_key': p['native_product_key'],
            'native_content_digest': p['native_content_digest'], 'segments': segments, 'text': endpoint['text']}


def short_anchors(anchors):
    result = {}
    for key, a in anchors.items():
        result[key] = {k: v for k, v in a.items() if k in ['packet', 'source_packet', 'passage_id', 'source_view_id',
                       'span', 'start', 'end', 'quote', 'text', 'native_pointer', 'native_text_pointer',
                       'coordinate_space', 'physical_pages', 'parent_physical_pages', 'source_ref', 'projection_digest', 'native_content_digest']}
    return result


def markdown_table(name, columns, rows):
    def cell(x):
        if isinstance(x, (list, dict)):
            x = json.dumps(x, ensure_ascii=False)
        return str(x).replace('|', '\\|').replace('\n', ' ')
    lines = ['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join('---' for _ in columns) + ' |']
    lines += ['| ' + ' | '.join(cell(x) for x in row) + ' |' for row in rows]
    (HERE / name).write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final-inputs', type=Path, help='Optional root-supplied pinned final evidence bundle; existence does not imply authentication.')
    args = parser.parse_args()
    dossier_path = 'assessment/final-source-capture/dossier-selection-assessment.json'
    if (ROOT / dossier_path).is_file():
        PATHS['dossier_assessment'] = dossier_path
    elif (ROOT / 'assessment/final-source-capture/dossier-native-selection-assessment.json').is_file():
        PATHS['dossier_native_assessment'] = 'assessment/final-source-capture/dossier-native-selection-assessment.json'
    data = {k: read(p) for k, p in PATHS.items()}
    assert data['final_named_transport']['outcome'] == 'passed'
    assert data['final_named_transport']['complete_report_bytes_equal']
    captures = {x['case_id']: x for x in data['final_source_capture']['cases']}
    model_cases = {x['case_id']: x for x in data['model_C']['source64_cases']}
    model_baseline = {x['baseline_component_id']:x for x in data['model_C']['baseline9_native_crosswalk']}
    old_packets, old_views = packet_inventory('source-packets')
    new_packets, new_views = packet_inventory('source-recovery/attempt001/source-packets')
    source_rows = []
    for group in sorted(old_packets):
        old = old_packets[group]
        new_path = 'source-recovery/attempt001/' + group
        new = new_packets[new_path]
        before = set().union(*(pages(old, v, True) for v in old['views']))
        after = set().union(*(pages(new, v, True) for v in new['views']))
        native_old = sorted({(v['native_view']['native_task_id'], v['native_view']['native_product_key'], v['native_view']['native_content_digest']) for v in old['views']})
        native_new = sorted({(v['native_view']['native_task_id'], v['native_view']['native_product_key'], v['native_view']['native_content_digest']) for v in new['views']})
        source_rows.append({'source_excerpt': old['source_pdf'], 'old_packet': citation(group, ''), 'recovered_packet': citation(new_path, ''),
                            'old_view_count': len(old['views']), 'recovered_view_count': len(new['views']),
                            'old_projected_pages': sorted(before), 'recovered_projected_pages': sorted(after), 'newly_available_pages': sorted(after-before),
                            'same_native_product_identity': native_old == native_new, 'old_native_products': native_old, 'recovered_native_products': native_new,
                            'old_selected_native_item_pages': sorted(set().union(*(pages(old, v, False) for v in old['views']))),
                            'recovered_selected_native_item_pages': sorted(set().union(*(pages(new, v, False) for v in new['views']))),
                            'semantic_capture': 'unassessed_by_availability_comparison', 'graphic_fidelity': 'unassessed'})
    current = data['current_C']['entries']
    current_rows = []
    for i, entry in enumerate(current):
        narrow = entry['narrow_public_attachment']
        observed = entry['actual_component']
        classification = ('wrong_subject_spurious_explanation_of_Y' if i == 12 else 'spurious_performed_definition_speech_act' if i == 21
                          else 'unresolved_named_concept_identity' if i == 31 else 'supported_local_partial_attachment')
        current_rows.append({'component_id': entry['component_id'], 'ordinal': i+1, 'observed': observed,
                             'C_facets': entry['C_six_facets'], 'C_narrow_attachment': narrow,
                             'A_expectation': entry['reviewer_A']['independently_authored_expectation'], 'B_facets': entry['reviewer_B']['facets'],
                             'B_narrow_attachment': entry['reviewer_B']['narrow_positive_attachment'],
                             'disagreements': entry['disagreements_and_classification_differences'],
                             'classification': classification, 'corrected_alternatives': entry['corrected_source_alternatives'],
                             'qualification_loss': 'Local qualifiers/arguments/antecedents omitted from this component; no claim of loss from all product families.',
                             'condition_scope_detail': narrow['qualifier_limits'],
                             'source_pin': data['current_C']['source_pins'][entry['source_pin_key']],
                             'C_authority': citation(PATHS['current_C'], f'/entries/{i}'),
                             'final_named_capture': 'exact_run160_transport_existing_independent_judgment_preserved', 'final_model_capture': 'exact_unchanged_member_of_final_model44_existing_independent_judgment_preserved'})
    baseline_rows = []
    for i, entry in enumerate(data['baseline_C']['entries']):
        observed = entry['frozen_component']
        identity = {role: endpoint_identity(observed[role], old_views) for role in ['term', 'content']}
        exact = [e['component_id'] for e in current if observed['interpretation'] == e['actual_component']['interpretation'] and
                 identity == {role: endpoint_identity(e['actual_component'][role], new_views) for role in ['term', 'content']}]
        baseline_rows.append({'component_id': entry['component_id'], 'ordinal': i+1, 'observed': observed,
                              'C_facets': entry['C_facets'], 'C_disposition': entry['C_disposition'],
                              'A_facets': entry['reviewer_perspectives']['A']['facets'], 'B_facets': entry['reviewer_perspectives']['B']['facets'],
                              'disagreements': entry['disagreements_and_classification_reconciliation'], 'retained_relations': entry['retained_relations'],
                              'native_endpoint_identity': identity, 'exact_native_pair_in_current35': exact,
                              'bounded_comparison_state': 'same_native_pair_repeated_with_existing_independent_judgments' if exact else 'exact_pair_not_repeated_in_current35_family',
                              'lost_scope': 'No whole-product loss claim. Nonrepetition of an unsupported pair is not proof a useful corrected reference was captured elsewhere.',
                              'C_authority': citation(PATHS['baseline_C'], f'/entries/{i}'),
                              'final_named_capture': 'exact_current35_to_run160_transport_authenticated_bounded_pair_comparison_only',
                              'final_model_capture': 'exact_native_pair_in_final44_with_independent_C_source_read',
                              'final_model_native_crosswalk': model_baseline[entry['component_id']]})
    a_common = {x['id']: x for x in data['common_A']['case_reviews']}
    b_common = {x['id']: x for x in data['common_B']['cases']}
    common_rows = []
    for i, case in enumerate(data['common_C']['cases']):
        ca, cb = a_common[case['id']], b_common[case['id']]
        common_rows.append({'case_id': case['id'], 'facet': case['facet'], 'pages': case['pages'], 'source_anchors': short_anchors(case['anchors']),
                            'A': {k: ca[k] for k in ['judgment', 'source_state', 'scope', 'facet_reviews', 'role_reviews', 'relationship_reviews', 'independent_expected', 'corrections_alternatives_missing_facets']},
                            'B': {k: cb[k] for k in ['scope', 'reason', 'role_judgments', 'relation_judgments', 'facet_judgments', 'corrections', 'missing_facets']},
                            'C': {k: case[k] for k in ['source_state', 'judgment', 'reason', 'scope', 'assertion_mode', 'roles', 'relations', 'facet_judgments', 'missing_facets', 'review_disposition']},
                            'frame': 'Same32-case source frame reviewed independently; not votes on812 authored records.',
                            'source_location': 'exact_native_bridge_with_explicit_caption_gaps', 'named_capture': captures[case['id']]['named']['state'],
                            'final_source_capture_C': captures[case['id']],
                            'model_capture': model_cases[case['id']]['model44_semantic_state'],
                            'final_model_C': model_cases[case['id']],
                            'C_authority': citation(PATHS['common_C'], f'/cases/{i}')})
    recovered_rows = []
    for i, case in enumerate(data['extra_C']['cases']):
        recovered_rows.append({'case_id': case['id'], 'facet': case['facet'], 'pages': case['pages'],
                               'source_anchors': short_anchors(case['anchors']),
                               'C': {k: case[k] for k in ['source_state', 'judgment', 'reason', 'scope', 'assertion_mode', 'roles', 'relations', 'missing_facets_or_limits']},
                               'independent_author_count': 1, 'A': 'not_run_for_this_extra_frame', 'B': 'not_run_for_this_extra_frame',
                               'named_capture': captures[case['id']]['named']['state'], 'model_capture': model_cases[case['id']]['model44_semantic_state'],
                               'final_model_C': model_cases[case['id']],
                               'final_source_capture_C': captures[case['id']],
                               'C_authority': citation(PATHS['extra_C'], f'/cases/{i}')})
    final_inputs = {'state': 'named_model_source_assessed_downstream_replays_pending', 'completed_inputs': [
        'Run152→160/cut210 full raw named report and all original source pins authenticated; nullable raw/inspection shape difference explicit.',
        'Set13 A43/B44/C45 exact typed-reference transport, SQL parents43/44 and two public normal/marginal attachments run169/cut225 retain original producer800.',
        'Independent C source-first64 named/scoped comparisons, selected actual policy/table/note/artifact occurrences and14 contextual private edges are supplied.',
        'All three actual feasibility/independent/coupled policy arms have exact same8210 IDs and84 cohorts/choices; bounded coupled assumptions and source meanings are assessed separately.',
        'Model161/cut245 finished/sealed97 raw envelopes, verified checkpoint/runtime, exact35 unchanged members inside44, all9 additions independently source-adjudicated and all64 bounded model-family comparisons supplied.',
        'Artifact183/task1070/cut247 completed; all13 distinct selected occurrences preserve their original fields and11 selected pairs have bounded downstream source judgments:7 useful textual lineages,4 contrary lexical alternatives.',
    ], 'exact_requirements': [
        'Completed repaired artifact/linking/dossier exports and independent source-semantic comparison, retaining original failed attempts; no generic retention promoted to computed policy.',
    ]}
    if args.final_inputs:
        supplied = json.loads(args.final_inputs.read_text())
        final_inputs.update({'state': 'supplied_pending_semantic_and_transport_review', 'bundle_path': str(args.final_inputs),
                             'bundle_sha256': hashlib.sha256(args.final_inputs.read_bytes()).hexdigest(), 'bundle': supplied,
                             'automatic_acceptance': False})
        pinned = []
        for item in supplied.get('artifacts', []):
            path = ROOT / item['path']
            if not path.is_file() or sha(item['path']) != item['sha256']:
                raise ValueError('Final input pin failed: '+item['path'])
            pinned.append(item)
        final_inputs['artifact_hashes_checked'] = pinned
    if 'dossier_assessment' in data:
        final_inputs['state'] = 'bounded_named_model_source_artifact_dossier_assessments_supplied'
        final_inputs['completed_inputs'].append('Both full current dossiers have exact membership/facet and selected-representation source assessments; original downstream failures remain preserved.')
        final_inputs['exact_requirements'] = []
    elif 'dossier_native_assessment' in data:
        final_inputs['state'] = 'native_dossier_assessed_portable_pending'
        final_inputs['completed_inputs'].append('Both native full dossier memberships, role/interpretation preservation and equal-budget selected representations are assessed. The first portable cross-cut closure failure remains separate.')
        final_inputs['exact_requirements'] = ['Both corrected verified dossier portable exports and the final matched-population receipt; native acceptance is not portable delivery.']
    input_paths = list(PATHS.values()) + sorted(old_packets) + sorted(new_packets)
    account = {'protocol': 'gs120-granular-benefit-account-2', 'date': '2026-11-06',
               'state': ('bounded_final_source_model_downstream_assessment_supplied' if 'dossier_assessment' in data else 'partial_final_named_model_source_account_dossier_portable_pending' if 'dossier_native_assessment' in data else 'partial_final_named_model_source_account_dossier_replay_pending'),
               'claim_boundary': 'An evidence-only assembly of selected independent judgments. No production change, automatic semantic capture, scientific truth, held-out efficacy or universal percentages.',
               'frames': {'baseline_output_components': 9, 'current_output_components': 35, 'final_model_components':44, 'model_additions':9,'common_reviewed_source_cases': 32, 'extra_recovered_C_source_cases': 32,
                          'original_authored_inventory_records': 812, 'distinct_independent_facts': False,
                          'denominator_policy': 'These selected frames overlap and differ in granularity. Never add them into a semantic denominator or vote across812 records.'},
               'original_inventory_limit': data['source_inventory_812'],
               'availability': {'old_view_count': len(old_views), 'recovered_view_count': len(new_views),
                                'old_projected_pages': sorted(set().union(*(set(x['old_projected_pages']) for x in source_rows))),
                                'recovered_projected_pages': sorted(set().union(*(set(x['recovered_projected_pages']) for x in source_rows))),
                                'newly_available_pages': sorted(set().union(*(set(x['newly_available_pages']) for x in source_rows))),
                                'native_identity_same_in_each_of12_excerpts': all(x['same_native_product_identity'] for x in source_rows),
                                'semantic_capture': 'not_established_by_coverage'},
               'dimension_contract': {'coverage': 'Source availability only; does not establish recognition fidelity or captured meaning.',
                                      'location': 'Exact bytes/pointer/provenance or physical overlap; overlap alone is never role/attachment support.',
                                      'role': 'Term/content/value/speech-act roles are judged independently.',
                                      'attachment': 'Exact directed local relation; corrected subjects/types do not retroactively credit actual outputs.',
                                      'condition_scope': 'Omitted qualification, assertion mode and contextual identity remain distinct from local attachment.',
                                      'fidelity': 'Original/converted recognition, graphics and source science are separate questions.',
                                      'loss': 'Nonrepetition or a missing qualifier in one named component is bounded to that family; no whole-product recall inference.',
                                      'spurious': 'An assessed wrong subject or speech act, never merely unmatched output or absent physical intersection.',
                                      'unresolved_unassessed': 'Ambiguity preserves a source/recognition question; unassessed preserves lack of semantic judgment.'},
               'preliminary_findings': [
                   'Availability expands from40 to48 views and recovers18 physical pages using the same12 native product identities; this is a verified availability change only.',
                   'The normal-density native pair is repeated across baseline9/current35. Eight other baseline exact pairs are not repeated in the current35 family; this is not a recall or correction score.',
                   'Current35 C judgments support32 local partial attachments, reject2 exact subject/speech-act pairs and leave1 truncated named concept ambiguous. Completeness/fidelity remain separate.',
                   'Three current formulas retain unsupported recognition fidelity while their source-owned local attachment remains useful.',
                   'All64 source cases now have independent C judgments against exact final named/scoped outputs: useful partial relationships, wrong subjects/roles, bounded misses and unresolved source recognition remain separate. Extra32 have no invented A/B votes.',
                   'Actual narrow table bindings are useful, but false native header flags cause semantic-header misses and ordinary prose can receive wrong procedure roles. Coupled symmetric all/none coherence weighting changes the candidate-relative joint while adding no source evidence or missing roles; calibration/semantic improvement is not established.',
                   'Two exact normal/marginal attachments are publicly readable under protected typed references and original producer800; all35 report components and48views remain in private closure, and four native refusal controls preserve the publication boundary.',
                   'Fourteen actual own-component contextual defined-by edges retain unassessed witnesses and the unsupported historical definition; custody transport is not independent attachment recovery.',
                   'The T>3/T>6 replay distinguishes lexical predicates but has unknown typed outcome, unestablished applicability and withheld interval consequence because explicit unit is absent.',
                   'The original artifact181 native configuration refusal and dossier182 reconstruction timeout remain failed attempts. Repaired artifact183 now retains142records/116candidatepairs;11selectedpairs have bounded source judgments, not calibrated identity truth. Earlier failures preserve the8210/35/2 upstream knowledge.',
                   'Final model44 retains exact35 named members and adds9: one useful local theorem application, one definition-location reference with interpretation limits and7 unsupported emitted pairs with corrected useful relationships. All9 baseline native pairs reappear; source authentication and fresh semantic judgment remain separate.',
                   'All97 model envelopes and5229 raw provider JSON reports are retained. Parsed syntax and zero annotation errors coexist with429 native-structure reports,437 unresolved native fields and thousands of unresolved/unlocated provider diagnostics. Other provider content remains semantically unassessed.',
               ],
               'frozen_inputs': [{'path': p, 'sha256': sha(p), 'bytes': (ROOT/p).stat().st_size} for p in input_paths],
               'source_availability_rows': source_rows, 'baseline9_rows': baseline_rows, 'current35_rows': current_rows,
               'source_common32_rows': common_rows, 'source_extra32_rows': recovered_rows, 'final_inputs': final_inputs}
    account['final_operational_evidence'] = {key: data[key] for key in ['final_named_transport','protected_reference','protected_publication','comparison','model_manifest','model_checkpoint','published_mcp']}
    semantic_keys = ['final_source_capture','contextual_assessment','policy_assessment','table_note_assessment','artifact_assessment','artifact_link_assessment','downstream_failures','model_C','model_provider_inventory','model_cli']
    if 'dossier_assessment' in data:
        semantic_keys.append('dossier_assessment')
    elif 'dossier_native_assessment' in data:
        semantic_keys.append('dossier_native_assessment')
    account['bounded_semantic_evidence'] = {key: citation(PATHS[key], '') for key in semantic_keys}
    account['artifact_link_assessment'] = data['artifact_link_assessment']
    if 'dossier_assessment' in data:
        account['dossier_selection_assessment'] = data['dossier_assessment']
    elif 'dossier_native_assessment' in data:
        account['dossier_native_selection_assessment'] = data['dossier_native_assessment']
    account['model9_additions']=data['model_C']['additions']
    account['provider_content_inventory_summary']={key:data['model_provider_inventory'][key] for key in ['task_counts','raw_report_parse_outcomes','annotation_errors','diagnostic_counts','execution_counts','native_content_state_counts','limits']}
    write('account.json', account)
    for key, filename in [('source_availability_rows','source-availability.json'), ('baseline9_rows','baseline9.json'),
                          ('current35_rows','current35.json'), ('source_common32_rows','source-common32.json'), ('source_extra32_rows','source-extra32.json')]:
        write(filename, account[key])
    markdown_table('source-availability.md', ['Excerpt','Old views','Recovered views','Newly available pages','Semantic capture'],
                   [[r['source_excerpt'],r['old_view_count'],r['recovered_view_count'],r['newly_available_pages'],r['semantic_capture']] for r in source_rows])
    markdown_table('baseline9.md', ['Baseline ID','Observed pair','C disposition','Exact pair in current35','Loss/capture limit'],
                   [[r['component_id'],r['observed']['term']['text']+' → '+r['observed']['content']['text'],r['C_disposition'],r['exact_native_pair_in_current35'],r['lost_scope']] for r in baseline_rows])
    markdown_table('current35.md', ['Current ID','Observed subject','Narrow attachment','Role/direction/type/recognition','Condition/scope limit','Final state'],
                   [[r['component_id'],r['observed']['term']['text'],r['C_narrow_attachment']['state'],
                     {k:v['judgment'] for k,v in r['C_facets'].items()},r['condition_scope_detail'],r['final_named_capture']] for r in current_rows])
    for name, rows in [('source-common32',common_rows),('source-extra32',recovered_rows)]:
        markdown_table(name+'.md', ['Source case','Facet','Pages','C source judgment','Scope/assertion mode','Named capture','Scoped disposition','Useful scoped fragment','Missing/wrong scoped meaning','Model'],
                       [[r['case_id'],r['facet'],r['pages'],r['C']['judgment'],r['C']['scope']+' / '+r['C']['assertion_mode'],r['named_capture'],
                         r['final_source_capture_C']['scoped']['state'],r['final_source_capture_C']['scoped']['useful_retained_distinction'],
                         r['final_source_capture_C']['scoped']['missing_or_wrong_meaning'],r['model_capture']] for r in rows])
    markdown_table('bounded-table-note.md', ['Source case','Selected actual bindings','Bounded judgment','Remaining source meaning'],
                   [[a['case_id'],[e['subject']['source_pointer']+' '+e['subject']['text']+' → '+e['target']['source_pointer']+' '+e['target']['text'] for e in a['selected_edges']],
                     a['judgment'],a['meaning']['missing_or_wrong_meaning']] for a in data['table_note_assessment']['audits']])
    markdown_table('policy-arms.md', ['Actual arm','Completed bands','Not-run operations','Selected source meaning','Policy limit'],
                   [[phase,counts.get('completed',0),counts.get('not_run',0),data['policy_assessment']['coupled_source_judgment'],
                     'Same8210 contributions/84 cohorts. Uniform unary assumptions; coupled symmetric all/none log2 factor. No source probability calibration or new semantic roles.']
                    for phase,counts in data['policy_assessment']['counts'].items()])
    markdown_table('model9-additions.md', ['Exact component ID','Observed pair','C judgment','Useful corrected/source relationship','Source scope limit'],
                   [[c['component_id'],c['actual_component']['term']['text']+' → '+c['actual_component']['content']['text'],c['C_state'],c['C_reason'],c['expected_local_meaning']] for c in data['model_C']['additions']])
    markdown_table('provider-content-states.md', ['Family','Diagnostic code','Role','Count','Meaning limit'],
                   [[d['family'],d['code'],d['role'],d['count'],'Content/recognition diagnostic retained; not distinct facts or semantic accuracy denominator.'] for d in data['model_provider_inventory']['diagnostic_counts']])
    markdown_table('artifact-links.md', ['Actual pair index','Left source artifact','Right source artifact','Candidate route','Diagnostic probability','Bounded source judgment'],
                   [[c['pair_index'], c['left']['artifact'], c['right']['artifact'], c['candidate_routes'], c['model_probability'], c['judgment']] for c in data['artifact_link_assessment']['cases']])
    if 'dossier_assessment' in data:
        markdown_table('dossier-representations.md', ['Policy','Actual run/cut/tasks','Full membership','Selected/omitted','Represented/missing already-supported facets','Selected source text'],
                       [[p['policy'], [p['run_id'],p['cut_id'],p['task_ids']], data['dossier_assessment']['full_members'],
                         [p['selected_count'],p['omitted_count']], [len(p['represented_facets']),len(p['missing_facets'])],
                         [m['citation']['text'] for m in p['selected_members']]] for p in data['dossier_assessment']['policies']])
    write('pending-final-inputs.json', final_inputs)
    print(json.dumps({'state': account['state'], 'frames': account['frames'], 'input_pins': len(input_paths), 'final_state': final_inputs['state']}))


if __name__ == '__main__':
    main()
