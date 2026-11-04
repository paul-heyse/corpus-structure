"""Freeze source-aligned descriptor/overlay corrections after the first integrated run."""
import json
import re
from hashlib import sha256
from pathlib import Path
source=Path(__file__).parent/'current-head-018'
state_bytes=(source/'native_operations.json').read_bytes();state=json.loads(state_bytes)
assert state['predecessor']=='semantic_m1_graph_20261104'
assert len(state['operations'])==3 and len(state['desired'])==151
assert {(x['after'] or x['before'])['identity']['name'] for x in state['operations']}=={'execution_contract_descriptor', 'source_record_gap_evidence', 'validate_source_record_reference_evaluation'}
admission=(source/'native_admission.sql').read_bytes()
versions=Path('python/corpus-structure/semantic_alembic/versions')
stem='semantic_m1_gaps_20261104'
code=f'''"""Retain protected source gaps and bounded consumer evidence."""
import json
from hashlib import sha256
from pathlib import Path
from alembic import op
from alembic.operations import Operations
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native
revision = "{stem}"
down_revision = "semantic_m1_graph_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "{stem}_native.json"
NATIVE_STATE_SHA256 = "{sha256(state_bytes).hexdigest()}"
NATIVE_ADMISSION_FILE = "{stem}_admission.sql"
NATIVE_ADMISSION_SHA256 = "{sha256(admission).hexdigest()}"
def _read(name,digest):
    content=Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest()!=digest:
        raise RuntimeError("M1 score artifact differs: "+name)
    return content

def upgrade():
    state=json.loads(_read(NATIVE_STATE_FILE,NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE,NATIVE_ADMISSION_SHA256)
    if state['predecessor']!=down_revision or state['version']!=1:
        raise RuntimeError("incompatible M1 score predecessor")
    for transition in state['operations']:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(),tuple(NativeObject.from_payload(item) for item in state['desired']))

def downgrade():
    raise RuntimeError("destructive M1 score downgrade refused")
'''
for name,content in {stem+'_native.json':state_bytes,stem+'_admission.sql':admission,'0121_m1_gap_consumers.py':code.encode()}.items():
 p=versions/name
 if p.exists():raise FileExistsError(name)
 p.write_bytes(content)
p=Path('python/corpus-structure/src/corpus_structure/semantic/execution_admission.py');s=p.read_text()
for name,constant in [('execution_contract_descriptor','_DESCRIPTOR_SHA256'),('require_execution_release','_REQUIRE_SHA256')]:
 item=next(item for item in state['desired'] if item['identity']['schema']=='data' and item['identity']['name']==name)
 s=re.sub(rf'{constant} = "[a-f0-9]+"',f'{constant} = "{sha256(item["catalog"]["body"].encode()).hexdigest()}"',s)
p.write_text(s)
print('frozen121:3 changes,151 managed objects')
