"""Frozen bound-only analytical execution source provenance.

The single descriptor transition records removal of installed analytical fallbacks.
Physical metadata and native function policy remain unchanged.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_bound_only_20261102"
down_revision = "semantic_ocr_inventory_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_bound_only_20261102_native.json"
NATIVE_STATE_SHA256 = "c38d59a6929592c8522eb6e9e3f121ae5d2df83c72ba09313868cccf4587288c"
NATIVE_ADMISSION_FILE = "semantic_bound_only_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "93962a21c69b5d4a2c6cfc5f69c572b31e73cd0fea392840e32182a8f0704185"


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
