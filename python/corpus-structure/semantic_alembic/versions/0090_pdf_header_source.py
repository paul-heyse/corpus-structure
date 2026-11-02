"""Frozen source-bound record-first native header routing.

Native functions, support policy and validation epoch v5 remain unchanged. The
single descriptor transition captures the maintained header reader implementation.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pdf_header_20261102"
down_revision = "semantic_op_read_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_header_20261102_native.json"
NATIVE_STATE_SHA256 = "6d7deb684b2305ad330c313535469d37e2f416f54c468b9a8f23286bfda575fc"
NATIVE_ADMISSION_FILE = "semantic_pdf_header_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "18d0432ab7b9abf3c88883de5701f0d74841c5d76f8e83dcc43bdc9d95faea13"


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
