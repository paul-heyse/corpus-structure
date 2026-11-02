"""Frozen current-model named row shapes and native release admission.

All column properties and ordered key vectors remain enforced. Column-name ordering
preserves exact named shapes across ordinary append-column evolution.83 remains
immutable; this successor performs only its two frozen native transitions.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_um_admit_20261102"
down_revision = "semantic_um_model_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_um_admit_20261102_native.json"
NATIVE_STATE_SHA256 = "e062a260585cf214f06a52677c24298a94621281fc13fd6380fec16988eedebd"
NATIVE_ADMISSION_FILE = "semantic_um_admit_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "0b20842b8789bb2d2b908a31bd63531420f36b27b5c10559f0f6af281d7050fb"


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
