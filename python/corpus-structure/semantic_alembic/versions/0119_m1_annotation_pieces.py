"""Reconstruct omitted separator item references as explicit unavailable locations."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_pieces_20261104"
down_revision = "semantic_m1_retained_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_pieces_20261104_native.json"
NATIVE_STATE_SHA256 = "da4f0be9078cbf9371ff4b6f7c34c25dc558eef225cd0afa2d27e72768f4ed58"
NATIVE_ADMISSION_FILE = "semantic_m1_pieces_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "86fb6d663f76d514391847a890ac7afb3b693e43a8fe8fdb17c69dd813e8596d"
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
