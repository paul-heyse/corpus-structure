"""Frozen exact coverage supports and immutable published validation receipts.

Current validation uses epoch v5; published readers retain their original receipt.
All mixed native payloads are preflighted before effects on the caller transaction.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pdf_support_20261102"
down_revision = "semantic_um_core_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_support_20261102_native.json"
NATIVE_STATE_SHA256 = "7cf083bf4c94aa4da6140a3faa1e0b7cfa920e2b7e364fc42eec2a057d65685d"
NATIVE_ADMISSION_FILE = "semantic_pdf_support_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "6f0ce9a963e883a469e09169a201aab8d4b00ffca5d87ba8e512894a630e0459"


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
