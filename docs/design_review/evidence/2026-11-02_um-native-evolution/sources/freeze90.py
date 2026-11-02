import json
from hashlib import sha256
from pathlib import Path

base=Path('python/corpus-structure/semantic_alembic/versions')
source=Path('build/um90-author-attempt-001')
state=json.loads((source/'native.json').read_bytes())
report=json.loads((source/'result.json').read_bytes())
assert state['predecessor']=='semantic_op_read_20261102'
assert len(state['operations'])==1 and report['ordinary_operations']==0 and not report['physical_alias']
label='semantic_pdf_header_20261102'
for suffix in ('native.json','admission.sql'):
    target=base/(label+'_'+suffix)
    assert not target.exists()
    content=(source/suffix).read_bytes()
    assert sha256(content).hexdigest()==report['artifacts'][suffix]
    target.write_bytes(content)
wrapper=(base/'0089_operation_read_source.py').read_text()
wrapper='''"""Frozen source-bound record-first native header routing.

Native functions, support policy and validation epoch v5 remain unchanged. The
single descriptor transition captures the maintained header reader implementation.
"""

'''+wrapper[wrapper.index('import json'):]
wrapper=wrapper.replace('revision = "semantic_op_read_20261102"','revision = "'+label+'"')
wrapper=wrapper.replace('down_revision = "semantic_pdf_callback_20261102"','down_revision = "semantic_op_read_20261102"')
wrapper=wrapper.replace('semantic_op_read_20261102_native.json',label+'_native.json')
wrapper=wrapper.replace('semantic_op_read_20261102_admission.sql',label+'_admission.sql')
wrapper=wrapper.replace('10d2012013bd46a9e425d615d16033af527ef7ae709eb1f1a387a51f0be12544',report['artifacts']['native.json'])
wrapper=wrapper.replace('b5947914eb414862aca0dbcdf7b0f719cf9784ad4ea783afd28288c8afb2a30c',report['artifacts']['admission.sql'])
target=base/'0090_pdf_header_source.py'
assert not target.exists()
target.write_text(wrapper)
for obj in state['desired']:
    if obj['identity']['name'] in ('execution_contract_descriptor','require_execution_release'):
        print(obj['identity']['name'],sha256(obj['catalog']['body'].encode()).hexdigest())
print('Frozen',label,'one descriptor transition')
