"""Whole-reading overlays, protected finite policy instances and scoped task reuse."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_admission_20261104"
down_revision = "semantic_m1_preparation_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_admission_20261104_native.json"
NATIVE_STATE_SHA256 = "42ea047178383a1f43038c23950a50c223a5030d38f475bc9e9067a9b223d240"
NATIVE_ADMISSION_FILE = "semantic_m1_admission_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "48d18ed6fa152ebb7fffc67f07a0ce0a1d8b4e062585d70480a0ee1139039a98"
PHYSICAL_STATE_FILE = "semantic_m1_admission_20261104_physical.sql"
PHYSICAL_STATE_SHA256 = "b13c7404ebbadaaed396a8e0a8f0b85d57c5c82affbd08491ff4084acc478c48"

def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("M1 admission artifact differs: " + name)
    return content

def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    physical = _read(PHYSICAL_STATE_FILE, PHYSICAL_STATE_SHA256).decode()
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible M1 admission predecessor")
    op.execute(physical)
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))

def downgrade():
    raise RuntimeError(
        "destructive M1 admission downgrade refused; preserve old immutable realizations"
    )
