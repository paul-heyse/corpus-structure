"""Retain upstream task ownership across source graph groups."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_graph_20261104"
down_revision = "semantic_m1_pieces_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_graph_20261104_native.json"
NATIVE_STATE_SHA256 = "679d4d86e4390c37d1cf5a288a30b4742e24e50989bede4395509684718133be"
NATIVE_ADMISSION_FILE = "semantic_m1_graph_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "c6659de31f3fe9b86db09c1a4bb24d13d33cba73a80f827b46cb6a09b399a292"
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
