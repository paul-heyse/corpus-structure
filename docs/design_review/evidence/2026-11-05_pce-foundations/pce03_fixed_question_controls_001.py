"""Focused evidence-normalization controls; not a second source validator."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import sys
sys.dont_write_bytecode=True
from pce03_output_authoring_002 import normalized_capture
from pce03_native_assessment_001 import RAW,read,write,digest
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_contracts import anchor_identity

old=read('pce03-fixed-output-old-closure-002.json')
original=next(iter(old['captures'].values()))
expected=normalized_capture(original)
controls=[]
def differs(name,change):
    altered=deepcopy(original);change(altered)
    assert normalized_capture(altered)!=expected,name
    controls.append(dict(name=name,outcome='passed'))

# View aliases may change only with the already authenticated identical physical owner.
alias=deepcopy(original)
view=alias['physical_sources'].pop('42');view.update(view_id=999,source_key='evidence-only-alias')
alias['physical_sources']['999']=view
for op in alias['operations'].values():
    before='retained-source-map:'+sha256(canonical_bytes(op['retained_source_bindings'])).hexdigest()
    for binding in op['retained_source_bindings']:
        binding.update(current_source_view_id=999,current_source='evidence-only-alias')
    after='retained-source-map:'+sha256(canonical_bytes(op['retained_source_bindings'])).hexdigest()
    op['computation_dependencies']=[after if value==before else value for value in op['computation_dependencies']]
    for root in alias['roots'].values():
        if root['operation_key']==op['operation_key']:
            root['computation_dependencies']=[after if value==before else value for value in root['computation_dependencies']]
for root in alias['roots'].values():
    for pin in (root['pin'],*(anchor['pin'] for anchor in root['anchors'])):
        pin.update(source_view_id=999,source='evidence-only-alias')
    for anchor in root['anchors']:anchor['anchor_id']=anchor_identity(anchor)
assert normalized_capture(alias)==expected
controls.append(dict(name='identical-authenticated-physical-view-alias-preserves-every-complete-question',outcome='passed'))

def relation(cap):return next(root for root in cap['roots'].values() if root['endpoints'])
def composite(cap):return next(root for root in cap['roots'].values() if len(root['members'])>1)
differs('wrong-endpoint-role-refused',lambda cap:relation(cap)['endpoints'][0].update(role='wrong_role'))
differs('member-order-change-refused',lambda cap:composite(cap)['members'].reverse())
differs('raw-returned-value-change-refused',lambda cap:next(root for root in cap['roots'].values() if 'value' in root).update(value={'kind':'text','text':'substituted'}))
def physical_change(cap):
    source=cap['physical_sources']['42'];source['physical_descriptor']['document_content_hash']='0'*64
    source['physical_sha256']=sha256(canonical_bytes(source['physical_descriptor'])).hexdigest()
differs('different-physical-document-refused',physical_change)
def coordinate_change(cap):
    anchor=next(root for root in cap['roots'].values() if root['anchors'])['anchors'][0]
    anchor['pointer']='#/texts/0';anchor['anchor_id']=anchor_identity(anchor)
try:
    altered=deepcopy(original);coordinate_change(altered);normalized_capture(altered)
except ValueError:controls.append(dict(name='changed-source-subject-occurrence-refused',outcome='passed'))
else:raise AssertionError('changed physical occurrence must refuse')
for name,change in (
    ('missing-member-closure-refused',lambda cap:cap['roots'].pop(composite(cap)['members'][0])),
    ('malformed-source-map-proof-refused',lambda cap:next(iter(cap['operations'].values()))['computation_dependencies'].append('retained-source-map:invalid')),
):
    altered=deepcopy(original);change(altered)
    try:normalized_capture(altered)
    except (ValueError,KeyError):controls.append(dict(name=name,outcome='passed'))
    else:raise AssertionError(name)
result=dict(outcome='passed',scope='evidence-only full recursive question comparison; native source authentication remains separately owned',
    controls=controls,source_capture_sha256=digest(RAW/'pce03-fixed-output-old-closure-002.json'),
    normalizer_sha256=digest(Path(__file__).with_name('pce03_output_authoring_002.py')),script_sha256=digest(Path(__file__)))
write(RAW/'pce03-fixed-question-controls-001.json',result)
print(result)
