"""Fresh authored blank-cell state must not become captured structure from zero output."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
from dataclasses import asdict
from corpus_structure.evaluate import operation_assessment as assessment
from corpus_structure.semantic.identity import canonical_bytes
from pce03_native_assessment_001 import RAW,read,write,digest
x=read('pce03-fresh-source-wrappers-003.json');key='recover_returned_local_contributions:unit2'
f=assessment.decode_frame(x['frames'][key]);cases=assessment.decode_authored(canonical_bytes(x['payloads'][key]['C']['authored']),f)['cases']
c=next(c for c in cases if c.facet=='cell_literal' and c.source_state=='unstated')
r=assessment.score_cases(f,[c],[],endpoint_closure=[])
assert r['cases'][0]['judgment']=='unsupported'
assert r['cases'][0]['capture_outcome']=='not_captured'
assert r['cases'][0]['error_category']=='missing_output'
assert sum(r['absence_detection_facets'][c.facet].values())==0
write(RAW/'pce03-actual-absence-control-002.json',dict(outcome='passed',case=asdict(c),result=r,
    source_wrapper_sha256=digest(RAW/'pce03-fresh-source-wrappers-003.json'),script_sha256=digest(Path(__file__)),
    scope='Fresh independent actual native blank source subject, explicit structure question; empty prediction input is a controlled absence, never a captured unstated field'))
print(json.dumps(dict(outcome='passed',case_id=c.case_id)))
