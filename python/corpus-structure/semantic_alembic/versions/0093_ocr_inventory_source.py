"""Frozen current OCR inventory publication and read contracts.

Six current publication/read kernels and their descriptor follow the current
model-bound OCR inventory source. Physical metadata remains unchanged.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ocr_inventory_20261102"
down_revision = "semantic_report_cache_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_ocr_inventory_20261102_native.json"
NATIVE_STATE_SHA256 = "fa93f7f200fd0a0b4554fa68f2e513fd47c52cc361f444540e35080c4b4ea6aa"
NATIVE_ADMISSION_FILE = "semantic_ocr_inventory_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "5eded8e7c3221b9257c5cec35a754b0c04df400408ff05639dc8fcaa3eb87b2f"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen unified native admission artifact differs: " + name)
    return content


def upgrade() -> None:
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen unified native admission state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    transitions = tuple(NativeTransitionOp.from_payload(item) for item in state["operations"])
    operations = Operations(op.get_context())
    for transition in transitions:
        operations.invoke(transition)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("unified native admission downgrade refused; rebuild owned realization")
