"""Correct set-valued selection check and bind final formatted M1 implementation."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_score_20261104"
down_revision = "semantic_m1_admission_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_score_20261104_native.json"
NATIVE_STATE_SHA256 = "959e1f4cc137e25d28a62504c8e3622bf3520c37f1d6c0d61584e7404974aef8"
NATIVE_ADMISSION_FILE = "semantic_m1_score_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "9a83508b7bb1410cac4aaa0a9ed6115fd7f64b2f6902b052b0e550e11a732ac1"
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
