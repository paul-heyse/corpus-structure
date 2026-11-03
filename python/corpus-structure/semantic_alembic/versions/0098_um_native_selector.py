"""Frozen retained native selection source provenance.

Only the execution descriptor's model/input provenance changes.
Physical metadata, privileges and native guard policy remain unchanged.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_um_selector_20261103"
down_revision = "semantic_um_stdio_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_um_selector_20261103_native.json"
NATIVE_STATE_SHA256 = "b94c859829573e1958347e68aa1c46cc907bd347164edb245c12dbd0ea02e285"
NATIVE_ADMISSION_FILE = "semantic_um_selector_20261103_admission.sql"
NATIVE_ADMISSION_SHA256 = "937da5850c8cbfb83bf31172c90305c51cf60323c6566f2add1a49424a6ac7c9"


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
