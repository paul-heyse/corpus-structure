"""Bind reading resolver outcome dimension to the actual terminal field."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_outcome_20261104"
down_revision = "semantic_m1_resolve_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_outcome_20261104_native.json"
NATIVE_STATE_SHA256 = "3f589428ee92a38a4b1a81618aa3ac0279035a4974364c46a4c89edfd8c04e64"
NATIVE_ADMISSION_FILE = "semantic_m1_outcome_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "e64984e47d8eb798e8c0b447a7f5248914bc591538338b9b9f3b68c527e2e4c7"
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
