"""Assemble authored C source judgments with exact evidence citations; no DB access."""
from collections import Counter
from functools import cache
import hashlib
import json
from pathlib import Path

from corpus_structure.semantic.observations import source_python
from judgments import COMMON, EXTRA, NAMED

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUTS = set()


def read(path):
    INPUTS.add(path)
    return json.loads((ROOT / path).read_text())


@cache
def pin(path):
    return {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}


def citation(path, pointer=''):
    INPUTS.add(path)
    return pin(path) | {'json_pointer': pointer}


def write(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def lines(path):
    INPUTS.add(path)
    with (ROOT / path).open() as stream:
        for i, line in enumerate(stream, 1):
            yield i, json.loads(line)


def body(row):
    value = row['payload_json']
    return (json.loads(value) if isinstance(value, str) else value)['body']


def main():
    cp = 'authors/c/source-adjudication/adjudicated-source-cases.json'
    ep = 'authors/c/source-recovery-assessment/source-cases.json'
    common, extra = read(cp)['cases'], read(ep)['cases']
    assert len(COMMON) == len(EXTRA) == 32
    candidates = read('assessment/final-source-capture/candidate-locations.json')
    locations = {x['case_id']: x for x in candidates['cases']}
    transport = read('assessment/final-source-capture/native-source-correspondence.json')
    bridges = {x['case_id']: x for x in transport['cases']}
    current = read('authors/current-named-review/c/assessment.json')
    current_entries = {x['component_id']: x for x in current['entries']}
    final_report = read('assessment/run160-final-named001/task-800.json')['body']['structural_product']
    # Literal full-payload identity, not a source-semantic oracle.
    final_components = final_report['definition_components']['components']
    original_report = read('assessment/run152-current-named001/task-605.json')['body']['structural_product']
    assert original_report == final_report
    assert [x['component_id'] for x in final_components] == list(current_entries)
    for comp in final_components:
        # Inspection materializes this nullable default; raw producer omits it.
        assert 'effective_version' not in comp
        assert comp | {'effective_version': None} == current_entries[comp['component_id']]['actual_component']
    auth = read('assessment/run160-exact-transport001.json')
    assert auth['outcome'] == 'passed' and auth['complete_report_bytes_equal'] and auth['all_original_source_pins_equal']
    packet_views = {}
    # Original packet bytes are inputs to the old→current bridge, separately
    # pinned from the immutable native product/content/work identities.
    for path in sorted((ROOT / 'source-packets').glob('grinstead*.json')):
        read(str(path.relative_to(ROOT)))
    for path in sorted((ROOT / 'source-recovery/attempt001/source-packets').glob('grinstead*.json')):
        rel = str(path.relative_to(ROOT)); packet = read(rel)
        for view in packet['views']:
            packet_views[view['native_view']['id']] = (packet, view, rel)
    cases = []
    for frame, expected, judgs, authority in [('common32', common, COMMON, cp), ('extra32', extra, EXTRA, ep)]:
        for i, (case, judgment) in enumerate(zip(expected, judgs, strict=True)):
            case_id = case['id']; loc = locations[case_id]; state, useful, missing = judgment
            bridge = bridges[case_id]
            for a in bridge['anchors'].values():
                for seg in a['segments']:
                    packet, view, path = packet_views[seg['source_view_id']]
                    item = next(x for x in view['native_context']['items'] if x['self_ref'] == seg['native_pointer'])
                    page_map = {x['excerpt_physical_page']: x['parent_physical_page'] for x in packet['page_map']}
                    seg['source_work_sha256'] = packet['parent_pdf_sha256']
                    seg['excerpt_pdf_sha256'] = packet['source_pdf_sha256']
                    seg['parent_physical_pages'] = sorted({page_map[p['page_no']] for p in item.get('prov', [])})
            named_state, named_reason = NAMED.get(case_id, ('miss_in_bounded_named_family', 'No component in the exact final35 expresses this selected source case. Other machine families and full-source recall are separate questions.'))
            assert bool(loc['named_location_candidates']) == (case_id in NAMED)
            cases.append({
                'case_id': case_id, 'frame': frame, 'facet': case['facet'], 'pages': case['pages'],
                'independent_source_authors': ['A', 'B', 'C'] if frame == 'common32' else ['C'],
                'source_expectation': case, 'source_authority': citation(authority, f'/cases/{i}'),
                'exact_source_correspondence': bridge,
                'named': {'state': named_state, 'reason': named_reason,
                          'actual_component_ids': [c['component_id'] for c in loc['named_location_candidates']],
                          'existing_C_entry_pointers': [f"/entries/{list(current_entries).index(c['component_id'])}" for c in loc['named_location_candidates']],
                          'positive_whole_case_capture': False},
                'scoped': {'state': state, 'useful_retained_distinction': useful, 'missing_or_wrong_meaning': missing,
                           'candidate_citation': citation('assessment/final-source-capture/candidate-locations.json', f'/cases/{len(cases)}'),
                           'located_participant_ids': [p['contribution_id'] for p in loc['scoped_participant_candidates']],
                           'located_edge_ids': [p['contribution_id'] for p in loc['scoped_edge_candidates']],
                           'review_extent': 'Case-level source/role/edge-family inspection. Individual edge semantic verdicts are bounded to explicitly selected table/note/artifact/contextual records; remaining individual edges are unassessed.',
                           'remaining_alternative_semantics': 'unassessed outside these source-anchored candidates; no global miss or whole-case support inferred'},
                'facets': {
                    'location': 'exact_native_bridge_with_named_caption_gaps' if any(a['state'] == 'native_coordinate_gap' for a in bridge['anchors'].values()) else 'exact_native_bridge',
                    'role': state, 'attachment': 'partial_selected_local_bindings' if state == 'partial' else 'not_supported_as_expected_source_relationship',
                    'condition': {'state': 'not_fully_captured_in_selected_output', 'expected_scope': case['scope']},
                    'scope': {'state': 'bounded_local_candidates_only', 'source_scope': case['scope']},
                    'fidelity': {'state': 'literal_retention_is_not_recognition_repair', 'source_judgment': case['judgment'], 'limits': missing},
                },
                'model': {'state': 'unassessed_pending_completed_run161_manifest_and_independent_source_judgment'},
                'corrections_credit': 'Frozen expected source alternatives are reference judgments, never substituted into observed output.'})
    model_path='assessment/final-source-capture/model161-assessment.json'
    model_cases={c['case_id']:c for c in read(model_path)['source64_cases']} if (ROOT/model_path).exists() else {}
    if model_cases:
        for case in cases:
            case['model']={'state':'bounded_final_model44_assessed_other_provider_fields_unassessed', 'assessment':model_cases[case['case_id']],
                           'authority':citation(model_path,'/source64_cases/'+str(list(model_cases).index(case['case_id'])))}
    downstream_supplied = all((HERE/name).is_file() for name in ['artifact-link-assessment.json','dossier-selection-assessment.json'])
    write('source-capture-assessment.json', {
        'protocol': 'gs120-source-first-final-capture-C-1', 'date': '2026-11-06',
        'state': ('bounded_named_scoped_model_assessed_downstream_in_separate_accounts' if downstream_supplied else 'partial_named_scoped_model_assessed_downstream_replays_pending') if model_cases else 'partial_named_and_scoped_assessed_model_pending',
        'downstream_assessment_paths': ['artifact-link-assessment.json','dossier-selection-assessment.json'] if downstream_supplied else [],
        'frame': 'Selected common32 plus extra32 source-first cases; exposed shared development sources, no held-out cases.',
        'exposure': 'C previously authored common32,extra32,baseline9,current35 and protected4; inspected frozen A/B reviews. This is informed independent adjudication, not blinded validation.',
        'population_limits': 'The common32 have independent A/B/C accounts; the extra32 are C-only. 812 earlier authored records are not812 distinct cases, votes or a capture denominator.',
        'semantic_method': 'Original source quotes and roles precede judgment. Native pointer/field/cell-index/local-offset plus identical leaf and source-work bytes authenticate location only. No fuzzy aliases or production public-statement projection authors the expected meaning.',
        'native_transport_receipt': citation('assessment/run160-exact-transport001.json'),
        'raw_inspection_shape': 'Raw605 and raw800 structural_product objects are exactly equal. Frozen inspection actual_component materializes only effective_version:null; raw producers omit that key. Both shapes retained, never represented as identical serialized bytes.',
        'cases': cases,
        'case_dispositions': {'named': dict(Counter(x['named']['state'] for x in cases)), 'scoped': dict(Counter(x['scoped']['state'] for x in cases))},
        'whole_case_capture_claim': 'not_established', 'scientific_truth': 'unassessed', 'full_corpus_efficacy': 'not_claimed'})

    audited_cells={'GS120-COMMON-005':['#/tables/0/data/table_cells/8','#/tables/0/data/table_cells/9'],
        'GS120-COMMON-013':['#/tables/0/data/table_cells/3','#/tables/1/data/table_cells/3'],
        'GS120-COMMON-018':['#/tables/0/data/table_cells/8','#/tables/0/data/table_cells/9'],
        'GS120-RECOVERED-C-003':['#/tables/0/data/table_cells/3','#/tables/0/data/table_cells/4'],
        'GS120-RECOVERED-C-016':['#/tables/1/data/table_cells/4','#/tables/1/data/table_cells/5','#/tables/1/data/table_cells/6','#/tables/1/data/table_cells/7']}
    audited_edges={cid:{e['contribution_id'] for e in locations[cid]['scoped_edge_candidates']
        if e['value']['relation'] in ['header','row_label'] and e['subject'].get('source_pointer') in cellptrs}
        for cid,cellptrs in audited_cells.items()}
    # Keep administrative completed-scope counts distinct from inspected semantic bands.
    policy_bands = []
    population_ids={};population_records={};cohorts={}
    for phase in ['review-feasibility', 'review-independent', 'review-coupled']:
        population_ids[phase]=set();population_records[phase]={};cohorts[phase]={}
        path = f'current-structural-journey/sources002/{phase}/reports.jsonl'
        for n, row in lines(path):
            report = body(row)
            if report.get('method') != 'structure.scoped_relations':
                continue
            for contribution in report['contributions']:
                cid=contribution['contribution_id']
                assert cid not in population_ids[phase]
                population_ids[phase].add(cid)
                population_records[phase][cid]=hashlib.sha256(json.dumps(contribution,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
            for oi, op in enumerate(report['contribution_operations']):
                local = op.get('local_interpretation')
                if not local:
                    continue
                q = source_python(local['request']) if 'request' in local else None
                result = source_python(local['result']) if 'result' in local else None
                decisions = [x['key'] for x in q['decisions']] if q else []
                cohorts[phase][op['operation_key']]={'contribution_ids':local['contribution_ids'], 'decisions':q['decisions'] if q else None}
                intersect = []
                for case in cases:
                    ids = set(case['scoped']['located_edge_ids'])
                    if ids.intersection(decisions):
                        intersect.append(case['case_id'])
                selected = [cid for cid,ids in audited_edges.items() if ids.intersection(decisions)]
                policy_bands.append({'phase': phase, 'file': pin(path), 'line': n, 'operation_index': oi,
                    'operation_key': op['operation_key'], 'question': op['question'], 'outcome': local['outcome'],
                    'policy_version': local['policy_version'], 'policy_mode': local['policy_mode'],
                    'coupling_enabled': local['coupling_enabled'], 'probability_standing': local['probability_standing'],
                    'contribution_ids': local['contribution_ids'], 'source_case_intersections': intersect,
                    'meaning_assessment': 'selected_narrow_source_header_bindings_only_other_decisions_unassessed_policy_not_calibrated' if selected else 'unassessed_other_band_semantics',
                    'individually_assessed_source_cases':selected,
                    'request_pointer': f'/body/contribution_operations/{oi}/local_interpretation/request',
                    'result_pointer': f'/body/contribution_operations/{oi}/local_interpretation/result',
                    'request_digest': local.get('request_digest'), 'result_digest': local.get('result_digest'),
                    'decision_ids': decisions, 'constraint_count': len(q['constraints']) if q else None,
                    'potentials': q['potentials'] if q and selected else None,
                    'dependence_scopes': q['dependence_scopes'] if q and selected else None,
                    'assumptions': ('Selected coupled bands add a shared factor favouring all-applies and all-does_not_apply equally (log2 bonus), without eliminating mixed or all-none alternatives. A shared header is a source cue for grouping; symmetric coherence preference is an explicit policy assumption, not source-derived confidence.' if phase=='review-coupled' else 'The selected feasibility/independent bands use uniform unary values[0,0], no constraints and no dependence scope; both applies and does_not_apply remain allowed. These are policy assumptions, not source-derived confidence.') if selected else None,
                    'result_summary': {k: result[k] for k in ['outcome','probability_standing','exact_retained_support','detail']} if result else None,
                    'inspected_decision_marginals': [x for x in result['marginals'] if x['decision'] in set().union(*(audited_edges[cid] for cid in selected))] if result and selected else [],
                    'returned_alternatives': [{'choices':a['choices'],'probability':a['probability']} for a in result['alternatives']] if result and selected else [],
                    'alternative_selection': 'Only selected returned alternatives are exported; support/computation success does not choose a source-correct joint or establish probability calibration.'})
    assert population_ids['review-feasibility']==population_ids['review-independent']==population_ids['review-coupled']
    assert cohorts['review-feasibility']==cohorts['review-independent']==cohorts['review-coupled']
    assert len(population_ids['review-coupled'])==8210 and len(cohorts['review-coupled'])==84
    write('policy-band-assessment.json', {'protocol': 'gs120-bounded-source-policy-C-1',
        'bands': policy_bands,
        'counts': {phase: dict(Counter(b['outcome'] for b in policy_bands if b['phase'] == phase)) for phase in population_ids},
        'matched_population_authority':citation('current-structural-journey/sources002/matched-populations.json'),
        'independent_population_check':{'same8210_contribution_ids':True,'same84_operation_cohorts_and_choices':True,
            'full_contribution_record_digest_maps_equal':population_records['review-feasibility']==population_records['review-independent']==population_records['review-coupled']},
        'coupled_source_judgment':'Selected correctly located source header bindings remain useful across arms. Coupling retains the contrary all-none assignment and unassessed other-cell assignments, adds no missing semantic header/footnote/unit roles and does not establish semantic improvement. Symmetric all/none coherence weighting is not source support or calibration.',
        'limits': 'No likelihood or calibration inferred from geometry, native header flags, uniform factors, marginals, solver success or shared support. Generic no-policy retention remains not_run, not v2 computation; oversized bands remain not_run.'})

    table_cases = ['GS120-COMMON-005','GS120-COMMON-013','GS120-COMMON-015','GS120-COMMON-018','GS120-COMMON-024','GS120-COMMON-021','GS120-RECOVERED-C-003','GS120-RECOVERED-C-015','GS120-RECOVERED-C-016']
    # Narrow supported table endpoints are individually selected from source positions.
    selected_cells = {'GS120-COMMON-005': ['#/tables/0/data/table_cells/8','#/tables/0/data/table_cells/9'],
        'GS120-COMMON-013': ['#/tables/0/data/table_cells/3','#/tables/1/data/table_cells/3'],
        'GS120-COMMON-015': [p['value']['source_pointer'] for p in locations['GS120-COMMON-015']['scoped_participant_candidates'] if p['value'].get('text') in ['x < µ 2σ','F']],
        'GS120-COMMON-018': ['#/tables/0/data/table_cells/8','#/tables/0/data/table_cells/9'],
        'GS120-RECOVERED-C-003': ['#/tables/0/data/table_cells/3','#/tables/0/data/table_cells/4'],
        'GS120-RECOVERED-C-015': [p['value']['source_pointer'] for p in locations['GS120-RECOVERED-C-015']['scoped_participant_candidates'] if p['value'].get('text') in ['- v','-u']],
        'GS120-RECOVERED-C-016': ['#/tables/1/data/table_cells/4','#/tables/1/data/table_cells/5','#/tables/1/data/table_cells/6','#/tables/1/data/table_cells/7']}
    audits = []
    for cid in table_cases:
        c = next(x for x in cases if x['case_id'] == cid); loc = locations[cid]
        selected_edges = [e for e in loc['scoped_edge_candidates'] if e['value']['relation'] in ['header','row_label'] and e['subject'].get('source_pointer') in selected_cells.get(cid, [])]
        audits.append({'case_id': cid, 'source_authority': c['source_authority'], 'source_expectation': c['source_expectation'],
            'selected_edges': selected_edges, 'judgment': 'supported_literal_local_header_or_row_binding_only' if selected_edges else 'expected_semantic_header_or_note_binding_not_captured',
            'relation_orientation': 'Actual subject is cell and target is its header/row label: cell has-header target. This is not silently relabelled as a source-authored header→cell edge.',
            'meaning': c['scoped'], 'source_conditions_and_ambiguity': c['source_expectation']['scope'],
            'probability_calibration': 'not_assessed_and_not_inferred'})
    write('table-note-assessment.json', {'protocol':'gs120-bounded-table-note-C-1','audits':audits,'other_table_cells_and_edges':'unassessed unless explicitly selected above'})

    artifact_cases = ['GS120-COMMON-006','GS120-COMMON-013','GS120-COMMON-032','GS120-RECOVERED-C-004','GS120-RECOVERED-C-031','GS120-RECOVERED-C-032']
    artifacts = []
    for cid in artifact_cases:
        case = next(x for x in cases if x['case_id'] == cid)
        refs = {(s['source_view_id'], s['native_pointer']) for a in case['exact_source_correspondence']['anchors'].values() for s in a['segments']}
        files = sorted({p['file'] for p in locations[cid]['scoped_participant_candidates']})
        for path in files:
            for n, envelope in lines(path):
                row = envelope['row']
                if envelope['population'] != 'interpretation' or row.get('semantic_type') != 'structural.artifact':
                    continue
                val = source_python(row['value'])
                if (row['source_view_id'], val['source_pointer']) not in refs:
                    continue
                packet, view, _ = packet_views[row['source_view_id']]
                assert val['source_work'] == packet['parent_pdf_sha256']
                artifacts.append({'case_id':cid,'file':pin(path),'line':n,'contribution_id':row['contribution_id'],'value':val,
                    'judgment':'supported_textual_caption_or_reference_occurrence_under_exact_work_and_code',
                    'limits':'Unknown revision and empty aliases retained. Occurrence roles do not by themselves resolve identity/links, convey graphic marks, prove fit, or bind caption parameters to all body formulas.'})
    write('artifact-occurrence-assessment.json', {'protocol':'gs120-source-artifact-occurrences-C-1','occurrences':artifacts,
        'native_caption_gap':'COMMON013 captions remain native_item_text without recovered projection; no arbitrary role coercion or invented spans.',
        'graphic_inspection':'unassessed in this task; frozen source-only account limits preserved',
        'linking_dossier':('Bounded downstream artifact-link and dossier-selection assessments are supplied separately; original occurrence judgments are unchanged and no fuzzy aliases are introduced.' if downstream_supplied else 'pending completed artifact/linking dossier for independent semantic assessment; no fuzzy aliases')})

    failures={name:{'evidence':read(path),'citation':citation(path)} for name,path in [
        ('artifact_native_ABI','current-structural-journey/sources002/artifact-native-abi-refusal.json'),
        ('dossier_native_timeout','current-structural-journey/dossier-native-fit/observed-failure.json'),
        ('dossier_registered_failure','current-structural-journey/dossiers001/failure.json')]}
    write('downstream-failure-account.json',{'protocol':'gs120-downstream-failures-C-1','failures':failures,
        'meaning':'Actual downstream artifact native configuration refusal and dossier reconstruction timeout have no accepted result at these attempts. Neither is a source semantic disagreement or evidence of lost upstream knowledge.',
        'preserved_upstream':'8210 scoped contributions,35 named components and2 protected public attachments remain separately retained. No source-case or full-family success is manufactured from a failed downstream operation.',
        'next':('Later completed repair/replay and bounded meaning assessments are supplied in artifact-link-assessment.json and dossier-selection-assessment.json. These original failed attempts stay failed and preserved.' if downstream_supplied else 'Completed repair/replay evidence and independent output meaning assessment remain pending; these failed attempts stay in the account.')})

    contextual = []
    for path in sorted((ROOT/'current-contextual-journey/contextual001').glob('source-*/retrieve-contextual-export/items.jsonl')):
        rel=str(path.relative_to(ROOT)); mentions={}
        for n, envelope in lines(rel):
            row=envelope['row']
            if envelope['population']!='interpretation':continue
            value=source_python(row['value'])
            if row['semantic_type']=='contextual.located_mention':
                mentions[row['contribution_id']]=source_python(value['producer_value'])['component_reference']
            elif row['semantic_type']=='contextual.relationship':
                assert len(row['members'])==1
                mention=mentions[row['members'][0]]
                assert mention and mention['component_id'] in current_entries
                entry=current_entries[mention['component_id']]
                assert value['relation']=='defined-by'
                assert value['target']['term']['text']==entry['actual_component']['term']['text']
                assert value['target']['content']['text']==entry['actual_component']['content']['text']
                for role in ['term','content']:
                    for key in ['start','end','text']:
                        assert value['target'][role][key]==entry['actual_component'][role][key]
                    assert value['target'][role]['scope']==entry['actual_component']['scope']
                contextual.append({'file':pin(rel),'line':n,'contribution_id':row['contribution_id'],
                    'component_reference':mention,'actual_relationship':value,
                    'source_attachment_judgment':entry['narrow_public_attachment']['state'],
                    'source_conditions_limits':entry['narrow_public_attachment']['qualifier_limits'],
                    'independent_C_entry':citation('authors/current-named-review/c/assessment.json',f"/entries/{list(current_entries).index(mention['component_id'])}"),
                    'witness_support':'unassessed_actual_workflow',
                    'credit':'own-component private edge; useful custody/transport, no independent usage-to-definition recovery or ranking/capture benefit'})
    assert len(contextual)==14
    write('contextual-attachment-assessment.json', {'protocol':'gs120-contextual-source-meaning-C-1','edges':contextual,
        'known_error_retained':'Historical instead-of-defining contrast is also selected as defined-by; local source judgment remains unsupported despite successful contextual transport.',
        'limits':'All35 components and48views retained; only14 emitted definitions selected,21 explanations not selected. Own-component witnesses are coupled to the producer; scientific/public truth and complete source capture remain unassessed.'})
    pins = [pin(p) for p in sorted(INPUTS | {'assessment/final-source-capture/judgments.py', 'assessment/final-source-capture/build_assessment.py'})]
    write('input-pins.json', {'protocol':'gs120-final-capture-input-pins-1','inputs':pins,'frozen_scoped_exports':candidates['scoped_input_files']})
    print(json.dumps({'source_cases':len(cases),'policy_operations':len(policy_bands),'table_note_audits':len(audits),'artifact_occurrences':len(artifacts),'contextual_edges':len(contextual),'inputs':len(pins)}))


if __name__=='__main__':
    main()
