"""Derive bounded actual results from authenticated stored-grade receipts."""
from pathlib import Path
from collections import Counter
import json,sys
sys.dont_write_bytecode=True
from pce03_native_assessment_001 import RAW,read,write,digest

def phase(report):
    units=[];total=Counter();errors=Counter();captures=Counter();facets={}
    for unit in report['result']['units']:
        for case in unit['cases']:
            total[case['judgment']]+=1;errors[case['error_category'] or 'none']+=1;captures[case['capture_outcome']]+=1
        for name,counts in unit['facets'].items():
            facets.setdefault(name,Counter()).update(counts)
        units.append(dict(unit_id=unit['unit_id'],source_view_id=unit['source_view_id'],prediction_count=unit['prediction_count'],
            prediction_count_grain=unit['prediction_count_grain'],producer_observation_count=unit['producer_observation_count'],
            producer_observation_count_grain=unit['producer_observation_count_grain'],facets=unit['facets'],
            absence_detection_facets=unit['absence_detection_facets'],producer_reports=unit['producer_reports'],
            producer_operation_outcomes=dict(Counter(value['outcome'] for value in unit['producer_operations'])),
            cases=[{key:value for key,value in case.items() if key not in {'explanation','candidate_ids'}} for case in unit['cases']]))
    return dict(evaluation_id=report['id'],set_id=report['set_id'],run_id=report['run_id'],case_facet_count=sum(total.values()),
        judgments=dict(total),error_categories=dict(errors),capture_outcomes=dict(captures),facets={key:dict(value) for key,value in facets.items()},units=units)
source=read('pce03-fresh-source-grade-005.json');output=read('pce03-fresh-output-grade-005.json');custody=read('pce03-fresh-custody-final-001.json')
sources={};outputs={}
for question,value in source['grades'].items():
    sources[question]=dict(baseline=phase(value['baseline']),revised=phase(value['revised']),
        paired_status_counts={key:len(rows) for key,rows in value['comparison']['changes'].items()})
for question,value in output['grades'].items():outputs[question]=phase(value)
source_total=Counter();output_total=Counter();paired=Counter()
for value in sources.values():source_total.update(value['revised']['judgments']);paired.update(value['paired_status_counts'])
for value in outputs.values():output_total.update(value['judgments'])
assert source_total==Counter(supported=16,unsupported=73,unassessed=4)
assert output_total==Counter(supported=3,unsupported=5,ambiguous=2,unassessed=14)
assert paired==Counter(newly_captured=16,unchanged=73,still_unresolved=4)
result=dict(outcome='passed',source_first=sources,output_first=outputs,source_first_actual_totals=dict(source_total),
    source_first_paired_totals=dict(paired),output_first_actual_totals=dict(output_total),
    source_selection_scope='Five source-selected text items across two views plus one table with16 source-hash-selected body cells;93 case facets; original feature-fit partition. No prediction-based source selection.',
    output_selection_scope='Original24 frozen semantic contribution products, stratified by kind and semantic type/question; preserved by exact complete recursive physical/semantic reidentification, not resampled.',
    interpretation='Finite selected-retained-output coverage and literal/field-state/declared binary attachment fidelity only.14 output events remain unassessed and2 ambiguous. Rich scientific roles are not inferred from literal captures; source misses do not identify a nomination, model, adapter or retrieval cause.',
    output_012_detail='The selected occurrence product exists with an item-level cell124 subject. Independent expectation requires exact .0217 literal coordinates. The scorer missing_output label means no exact literal candidate, not absence of the selected product or evidence of an unrun producer.',
    table_attachment_detail='All64 independent header/row/unit/note facets have missing_output; actual task97 index contains zero table attachment relation products. Explicit unstated unit/note fields do not become captured from silence.',
    stage_inventory=dict(source_only=read('pce03-source-run-003.json')['method_inventory'],retained_output=read('pce03-retained-products-run-003.json')['method_inventory'],
        retained_raw_input_tasks=[36,37],provider_execution=False,conversion=False,new_model_quality_claim='not_established'),
    stored_grade_ids=sorted(row['evaluation_id'] for row in custody['stored_evaluations']),
    artifacts={name:digest(RAW/name) for name in ['pce03-fresh-source-grade-005.json','pce03-fresh-output-grade-005.json','pce03-fresh-custody-final-001.json','pce03-fixed-output-reidentification-003.json']},
    protected_exports=dict(sets=[value['set_id'] for value in custody['reference_sets']],judgments_exposed=False),
    portable_complete_claim='not_established',population_estimate='not_established',model_quality='not_established',
    script_sha256=digest(Path(__file__)))
write(RAW/'pce03-actual-assessment-summary-001.json',result)
print(json.dumps({key:result[key] for key in ['outcome','source_first_actual_totals','source_first_paired_totals','output_first_actual_totals','stored_grade_ids']}))
