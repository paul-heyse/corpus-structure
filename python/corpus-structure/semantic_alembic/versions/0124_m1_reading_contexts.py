"""Admit retained reading contexts and bounded source support consumers."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_readings_20261104"
down_revision = "semantic_m1_terminal_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_readings_20261104_native.json"
NATIVE_STATE_SHA256 = "21752fb0993fcc7258fa57b600f04e2c6b4be4ea76433bbfbd65baf0a608de9f"
NATIVE_ADMISSION_FILE = "semantic_m1_readings_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "6d24ccdabe6d0b6a4fc1dd042bd0495e06228c97352c608ed2987a629a1f8aec"
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
