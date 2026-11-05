"""Freeze the reviewed additive candidate, including ordinary physical operations."""
import json
import re
from hashlib import sha256
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=HERE/'native141-candidate-001'
destination=Path('python/corpus-structure/semantic_alembic/versions')
revision='semantic_pce_denotation_20261105'
state=json.loads((source/'native_operations.json').read_bytes())
assert state['predecessor']=='semantic_pce_semantics_20261105'
artifacts={
    'native.json':(source/'native_operations.json').read_bytes(),
    'admission.sql':(source/'native_admission.sql').read_bytes(),
    'upgrade.txt':(source/'native_candidate.py').read_bytes(),
}
for suffix,content in artifacts.items():
    with (destination/(revision+'_'+suffix)).open('xb') as stream:stream.write(content)
code='''"""Repair denotation guard precedence without changing semantic output; forward only."""
import json
from hashlib import sha256
from pathlib import Path
from alembic import op
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_denotation_20261105"
down_revision = "semantic_pce_semantics_20261105"
branch_labels = None
depends_on = None
'''
for name,suffix in [('STATE','native.json'),('ADMISSION','admission.sql'),('UPGRADE','upgrade.txt')]:
    code+=f'NATIVE_{name}_FILE = "{revision}_{suffix}"\n'
    code+=f'NATIVE_{name}_SHA256 = "{sha256(artifacts[suffix]).hexdigest()}"\n'
code+='''

def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen local publication artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible local publication predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive local publication downgrade refused")
'''
with (destination/'0141_denotation_guard.py').open('x') as stream:stream.write(code)
p=Path('python/corpus-structure/src/corpus_structure/semantic/execution_admission.py')
code=p.read_text()
for name,key in [('execution_contract_descriptor','_DESCRIPTOR_SHA256'),('require_execution_release','_REQUIRE_SHA256')]:
    item=next(i for i in state['desired'] if i['identity']['schema']=='data' and i['identity']['name']==name)
    code,count=re.subn(rf'{key} = "[0-9a-f]+"',f'{key} = "{sha256(item["catalog"]["body"].encode()).hexdigest()}"',code)
    assert count==1
p.write_text(code)
print(json.dumps(dict(outcome='passed',revision=revision,native_operations=len(state['operations']),ordinary_operations_retained=True)))
