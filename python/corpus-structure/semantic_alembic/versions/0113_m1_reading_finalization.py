"""Finalize direct sealed record evidence through the common atomic boundary."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_finish_20261104"
down_revision = "semantic_m1_fit_scope_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_finish_20261104_native.json"
NATIVE_STATE_SHA256 = "0bb7c06223fcec68ad3914de9cf415f73bcd26025df7ce5d227ae3d074fba30c"
NATIVE_ADMISSION_FILE = "semantic_m1_finish_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "9f6002b6e73f447f8c639e9f9ed6a31cb46bc66419a8d31b91c89ac450cbc4e2"
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
