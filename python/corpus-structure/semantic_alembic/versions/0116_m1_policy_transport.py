"""Preserve typed policy objects through publication transport and retain archive reads."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_jsonb_20261104"
down_revision = "semantic_m1_outcome_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_jsonb_20261104_native.json"
NATIVE_STATE_SHA256 = "0e78491602bfc6fc3a0a144760ca4edaca4bde9b8fb73dae3aa3578d753bad0b"
NATIVE_ADMISSION_FILE = "semantic_m1_jsonb_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "ca7c7a217e13fa5589f26e05aa292ff29dde0c6bb8af239e1788e91f7aac734e"
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
