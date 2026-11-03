"""Frozen native PDF diagnostic-stream source provenance.

The freeze operation shortens its owner fence; worker diagnostics use stderr.
Physical metadata, privileges and required native ownership guards remain unchanged.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_um_stdio_20261102"
down_revision = "semantic_um_closure_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_um_stdio_20261102_native.json"
NATIVE_STATE_SHA256 = "e4fa5ef16e725d8d27887ee9ed61f49e867d78c35b7c129d808c6ffecc2a82fe"
NATIVE_ADMISSION_FILE = "semantic_um_stdio_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "62ef23a77002a92f7a8762a8bb02196ba94792a70f6176f1f788caed47184d71"


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
