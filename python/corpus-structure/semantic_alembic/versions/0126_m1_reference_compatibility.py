"""Preserve immutable source references across compatible execution successors."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_reference_20261104"
down_revision = "semantic_m1_reuse_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_reference_20261104_native.json"
NATIVE_STATE_SHA256 = "8b9268a617e0c138e5fa3a4af80a2c0d4df43189ce537cd2c7bcaf4d029f0d7f"
NATIVE_ADMISSION_FILE = "semantic_m1_reference_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "6fabf3b84e1d27fc90ee1ffc29d565ec9d922c78ff327d1baa24a8c9899a6449"
def _read(name,digest):
    content=Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest()!=digest:
        raise RuntimeError("M1 reference artifact differs: "+name)
    return content

def upgrade():
    state=json.loads(_read(NATIVE_STATE_FILE,NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE,NATIVE_ADMISSION_SHA256)
    if state['predecessor']!=down_revision or state['version']!=1:
        raise RuntimeError("incompatible M1 reference predecessor")
    for transition in state['operations']:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(),tuple(NativeObject.from_payload(item) for item in state['desired']))

def downgrade():
    raise RuntimeError("destructive M1 reference downgrade refused")
