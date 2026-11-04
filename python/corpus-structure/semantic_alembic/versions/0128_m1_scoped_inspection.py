"""Admit scoped native inspection with complete retained inventory validation."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_inspect_20261104"
down_revision = "semantic_m1_ref_scope_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_inspect_20261104_native.json"
NATIVE_STATE_SHA256 = "18c0df1db948a9b7231e186e2ef6b3443e98afa18d250a3724ebb754401b3285"
NATIVE_ADMISSION_FILE = "semantic_m1_inspect_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "04bd4a5e7658485c1530686f8ac8c592c471d32f916522839bc12e782910f6f6"
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
