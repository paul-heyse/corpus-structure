"""Freeze reviewed native106→107 declarations without editing any predecessor."""
import ast
import json
import re
from hashlib import sha256
from pathlib import Path

root=Path.cwd()
source=Path(__file__).parent/'candidate-006'
state_bytes=(source/'native_operations.json').read_bytes()
state=json.loads(state_bytes)
assert state['predecessor']=='semantic_m1_preparation_20261104'
assert len(state['desired'])==149
assert len(state['operations'])==32
module=ast.parse((source/'native_candidate.py').read_text())
insert=[node.args[0].value for node in ast.walk(module) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='execute' and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str) and node.args[0].value.startswith('INSERT INTO sem.physical_contract')]
assert len(insert)==1
physical=(source/'physical.sql').read_text()+insert[0]+';\n'
admission=(source/'native_admission.sql').read_bytes()
stem='semantic_m1_admission_20261104'
versions=root/'python/corpus-structure/semantic_alembic/versions'
code=f'''"""Whole-reading overlays, protected finite policy instances and scoped task reuse."""
import json
from hashlib import sha256
from pathlib import Path
from alembic import op
from alembic.operations import Operations
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "{stem}"
down_revision = "semantic_m1_preparation_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "{stem}_native.json"
NATIVE_STATE_SHA256 = "{sha256(state_bytes).hexdigest()}"
NATIVE_ADMISSION_FILE = "{stem}_admission.sql"
NATIVE_ADMISSION_SHA256 = "{sha256(admission).hexdigest()}"
PHYSICAL_STATE_FILE = "{stem}_physical.sql"
PHYSICAL_STATE_SHA256 = "{sha256(physical.encode()).hexdigest()}"

def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("M1 admission artifact differs: " + name)
    return content

def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    physical = _read(PHYSICAL_STATE_FILE, PHYSICAL_STATE_SHA256).decode()
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible M1 admission predecessor")
    op.execute(physical)
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))

def downgrade():
    raise RuntimeError("destructive M1 admission downgrade refused; preserve old immutable realizations")
'''
files={stem+'_native.json':state_bytes,stem+'_admission.sql':admission,stem+'_physical.sql':physical.encode(),'0107_m1_record_admission.py':code.encode()}
for name in files:
 if (versions/name).exists():raise FileExistsError(name)
for name,value in files.items():(versions/name).write_bytes(value)
p=root/'python/corpus-structure/src/corpus_structure/semantic/execution_admission.py'
s=p.read_text()
for name,constant in [('execution_contract_descriptor','_DESCRIPTOR_SHA256'),('require_execution_release','_REQUIRE_SHA256')]:
 item=next(item for item in state['desired'] if item['identity']['schema']=='data' and item['identity']['name']==name)
 s=re.sub(rf'{constant} = "[a-f0-9]+"',f'{constant} = "{sha256(item["catalog"]["body"].encode()).hexdigest()}"',s)
p.write_text(s)
print(json.dumps(dict(revision=stem,native_changes=32,managed_objects=149)))
