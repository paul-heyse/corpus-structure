"""Preserve exact policy binding JSON bytes in scalar transport; validate their typed meaning."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_binding_20261104"
down_revision = "semantic_m1_jsonb_20261104"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_binding_20261104_native.json"
NATIVE_STATE_SHA256 = "538a42861f4a010c81e4b7f7c5394aaf6bba6cf16797a8a7a589dcce7551801d"
NATIVE_ADMISSION_FILE = "semantic_m1_binding_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "e00086926b040929870d171b322fa8097971d4f1fcda04d09d532400eaf80bd1"
PHYSICAL_STATE_FILE = "semantic_m1_binding_20261104_physical.sql"
PHYSICAL_STATE_SHA256 = "bf4f25a7c833e94f4af037103ca39f1a325eeb84ebe1359a80705b78b4a4ec92"

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
