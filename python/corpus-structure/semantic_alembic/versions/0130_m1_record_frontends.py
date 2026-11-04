"""Admit explicit source policy6 and native record-v2 frontends."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_frontend_20261104"
down_revision = "semantic_m1_ref_alias_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_frontend_20261104_native.json"
NATIVE_STATE_SHA256 = "d1285d21f92276c3d5034dfcc1f76994ba14373bf2717344ca387b545717fedc"
NATIVE_ADMISSION_FILE = "semantic_m1_frontend_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "0ad988152ffe83640e9f3cf9fd4e6089e12884a23536d9b4005f30244207b2b9"
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
