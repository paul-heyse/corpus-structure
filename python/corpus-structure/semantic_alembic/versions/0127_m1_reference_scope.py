"""Disambiguate frozen-reference gap and fitting frame SQL scopes."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_ref_scope_20261104"
down_revision = "semantic_m1_reference_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_ref_scope_20261104_native.json"
NATIVE_STATE_SHA256 = "cb82d5202504b09be8f852a6fc8eba89ba30b445fc9d3c6d1a71479681729068"
NATIVE_ADMISSION_FILE = "semantic_m1_ref_scope_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "edccbc6876aa05798647f9f858acd5caba8de7cfdf10af3d9763950fa1e04611"
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
