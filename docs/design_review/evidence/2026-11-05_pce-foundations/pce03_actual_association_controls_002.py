"""Actual retained adapter → native reader → source-first scorer association controls."""
from pathlib import Path
from dataclasses import asdict
from hashlib import sha256
import sys,json
sys.dont_write_bytecode=True
from corpus_structure.evaluate import operation_assessment as assessment
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.settings import Settings
from pce03_native_assessment_001 import RAW,read,write,digest

wrappers=read('pce03-fresh-source-wrappers-003.json');key='propose_returned_role_attachments:unit2'
frame=assessment.decode_frame(wrappers['frames'][key])
cases=assessment.decode_authored(canonical_bytes(wrappers['payloads'][key]['C']['authored']),frame)['cases']
with open_runtime_engine(Settings(),'pce03-actual-association-control',purpose='read') as engine,engine.begin() as conn:
    prepared=open_release(conn,wrappers['release_id'])
    summary=read_source_contributions(conn,prepared=prepared,run_id=28,source_view_id=frame.pin['source_view_id'],cut_id=33,limit=10000)
    keys=tuple(row['operation_key'] for row in summary.operations if row['question']==frame.operation_question and row['operation_version']==frame.operation_version)
    inventory=read_source_contributions(conn,prepared=prepared,run_id=28,source_view_id=frame.pin['source_view_id'],cut_id=33,operation_keys=keys,
        anchor_scopes=frame.anchor_scopes,anchor_endpoint_roles=('cell_value',),include_details=True,limit=10000)
    assert not inventory.more
    ids={endpoint['contribution_id'] for value in inventory.contributions for endpoint in value.get('endpoints',())}
    endpoints=read_source_contributions(conn,prepared=prepared,run_id=28,source_view_id=frame.pin['source_view_id'],cut_id=33,
        contribution_ids=tuple(sorted(ids)),include_details=True,limit=10000)
    assert not endpoints.more
closure={value['contribution_id']:value for value in (*inventory.contributions,*endpoints.contributions)}
products=[(value,assessment._comparison_product(value,closure)) for value in inventory.contributions if value['semantic_type']=='table.header_path_attachment']
write(RAW/'pce03-actual-association-capture-002.json',dict(inventory=list(inventory.contributions),endpoints=list(endpoints.contributions),source_wrapper_sha256=digest(RAW/'pce03-fresh-source-wrappers-003.json')))
# Independently source-authored complete alternatives determine the positive association.
positive=None
for case in cases:
    if case.facet!='header_path_attachment':continue
    for raw,expanded in products:
        if any(assessment._matches(expanded,option) for option in case.alternatives):
            positive=(case,raw,expanded);break
    if positive:break
assert positive is not None,'actual bounded projection has no fully matching authored header association'
case,raw,expanded=positive
right_target=next(endpoint for endpoint in expanded['endpoint_semantics'] if endpoint['role']=='header_path')
wrong_subject=None
for other in cases:
    if other.facet!='header_path_attachment' or set(other.anchor_ids)==set(case.anchor_ids):continue
    for alternative in other.alternatives:
        target=next(endpoint for endpoint in alternative['endpoint_semantics'] if endpoint['role']=='header_path')
        if target['anchor_ids']==right_target['anchor_ids'] and assessment._matches(right_target['fields'],target['fields']):
            wrong_subject=other;break
    if wrong_subject:break
assert wrong_subject is not None,'no different independently selected cell with same correct header target'
correct=assessment.score_cases(frame,[case],[raw],endpoint_closure=list(closure.values()))
wrong=assessment.score_cases(frame,[wrong_subject],[raw],endpoint_closure=list(closure.values()))
assert correct['cases'][0]['judgment']=='supported'
assert wrong['cases'][0]['judgment']=='unsupported' and wrong['cases'][0]['capture_outcome']=='not_captured'
# A declared unstated source field still needs explicit inspection output.
recovery_key='recover_returned_local_contributions:unit2';recovery_frame=assessment.decode_frame(wrappers['frames'][recovery_key])
recovery_cases=assessment.decode_authored(canonical_bytes(wrappers['payloads'][recovery_key]['C']['authored']),recovery_frame)['cases']
blank=next(case for case in recovery_cases if case.facet=='cell_literal' and case.source_state=='unstated')
absent=assessment.score_cases(recovery_frame,[blank],[],endpoint_closure=[])
assert absent['cases'][0]['judgment']=='unsupported' and absent['cases'][0]['capture_outcome']=='not_captured'
result=dict(outcome='passed',run_id=28,cut_id=33,source_wrapper_sha256=digest(RAW/'pce03-fresh-source-wrappers-003.json'),
    actual_relation=raw,actual_endpoint_closure=[closure[e['contribution_id']] for e in raw['endpoints']],
    correct_case=asdict(case),wrong_cell_right_header_case=asdict(wrong_subject),correct_score=correct,wrong_subject_score=wrong,
    explicit_unstated_case=asdict(blank),zero_output_unstated_score=absent,
    scope='Finite actual retained adapter/native reader projection, not producer quality. Actual relation is unchanged; the same correct header belongs to a different source-selected cell.',
    script_sha256=digest(Path(__file__)))
write(RAW/'pce03-actual-association-controls-002.json',result)
print(json.dumps(dict(outcome='passed',positive_case=case.case_id,wrong_subject=wrong_subject.case_id)))
