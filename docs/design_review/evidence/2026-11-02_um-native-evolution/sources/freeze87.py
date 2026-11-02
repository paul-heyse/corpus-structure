import json
from hashlib import sha256
from pathlib import Path

base = Path('python/corpus-structure/semantic_alembic/versions')
source = Path('build/um87-author-attempt-001')
state = json.loads((source / 'native.json').read_bytes())
report = json.loads((source / 'result.json').read_bytes())
assert state['predecessor'] == 'semantic_um_core_20261102'
assert report['ordinary_operations'] == 0 and report['physical_alias'] is False
label = 'semantic_pdf_support_20261102'
for suffix in ('native.json', 'admission.sql'):
    target = base / (label + '_' + suffix)
    assert not target.exists(), target
    content = (source / suffix).read_bytes()
    assert sha256(content).hexdigest() == report['artifacts'][suffix]
    target.write_bytes(content)
wrapper = (base / '0086_unified_core_bindings.py').read_text()
wrapper = '''"""Frozen exact coverage supports and immutable published validation receipts.

Current validation uses epoch v5; published readers retain their original receipt.
All mixed native payloads are preflighted before effects on the caller transaction.
"""

''' + wrapper[wrapper.index('import json'):]
wrapper = wrapper.replace('revision = "semantic_um_core_20261102"', 'revision = "' + label + '"')
wrapper = wrapper.replace('down_revision = "semantic_um_observe_20261102"', 'down_revision = "semantic_um_core_20261102"')
wrapper = wrapper.replace('semantic_um_core_20261102_native.json', label + '_native.json')
wrapper = wrapper.replace('semantic_um_core_20261102_admission.sql', label + '_admission.sql')
wrapper = wrapper.replace('953da1fb9464c39c7cf7b3c91d9c8a1b106d04df9d2871f91c7108e20f6032c2', report['artifacts']['native.json'])
wrapper = wrapper.replace('48b03b2573f66f25df5f92c6c8ce1ed743951a46ddce5bb92bab9b37bf3641eb', report['artifacts']['admission.sql'])
target = base / '0087_pdf_support_validation.py'
assert not target.exists(), target
target.write_text(wrapper)
for obj in state['desired']:
    if obj['identity']['name'] in ('execution_contract_descriptor', 'require_execution_release'):
        print(obj['identity']['name'], sha256(obj['catalog']['body'].encode()).hexdigest())
print('Frozen:', label, len(state['operations']), 'native transitions')
