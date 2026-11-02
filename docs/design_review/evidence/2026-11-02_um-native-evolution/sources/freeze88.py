import json
from hashlib import sha256
from pathlib import Path

base=Path('python/corpus-structure/semantic_alembic/versions')
source=Path('build/um88-author-attempt-001')
state=json.loads((source/'native.json').read_bytes())
report=json.loads((source/'result.json').read_bytes())
assert state['predecessor']=='semantic_pdf_support_20261102'
assert len(state['operations'])==1 and report['ordinary_operations']==0 and not report['physical_alias']
label='semantic_pdf_callback_20261102'
for suffix in ('native.json','admission.sql'):
    target=base/(label+'_'+suffix)
    assert not target.exists()
    content=(source/suffix).read_bytes()
    assert sha256(content).hexdigest()==report['artifacts'][suffix]
    target.write_bytes(content)
wrapper=(base/'0087_pdf_support_validation.py').read_text()
wrapper='''"""Frozen source-bound provenance for the optional-support callback correction.

Native functions, support policy and validation epoch v5 remain unchanged. The
single descriptor transition retains the strict captured implementation identity.
"""

'''+wrapper[wrapper.index('import json'):]
wrapper=wrapper.replace('revision = "semantic_pdf_support_20261102"','revision = "'+label+'"')
wrapper=wrapper.replace('down_revision = "semantic_um_core_20261102"','down_revision = "semantic_pdf_support_20261102"')
wrapper=wrapper.replace('semantic_pdf_support_20261102_native.json',label+'_native.json')
wrapper=wrapper.replace('semantic_pdf_support_20261102_admission.sql',label+'_admission.sql')
wrapper=wrapper.replace('7cf083bf4c94aa4da6140a3faa1e0b7cfa920e2b7e364fc42eec2a057d65685d',report['artifacts']['native.json'])
wrapper=wrapper.replace('6f0ce9a963e883a469e09169a201aab8d4b00ffca5d87ba8e512894a630e0459',report['artifacts']['admission.sql'])
target=base/'0088_pdf_callback_source.py'
assert not target.exists()
target.write_text(wrapper)
for obj in state['desired']:
    if obj['identity']['name'] in ('execution_contract_descriptor','require_execution_release'):
        print(obj['identity']['name'],sha256(obj['catalog']['body'].encode()).hexdigest())
print('Frozen',label,'one descriptor transition')
