"""Frozen observation-only writes, directional JSON projections and reader retirement.

The two obsolete report readers retire explicitly. Current writes use the guarded
observation entry; historical generic kernels and all frozen predecessors remain.
All payloads are preflighted before effects on the caller-owned transaction.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_um_observe_20261102"
down_revision = "semantic_um_admit_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_um_observe_20261102_native.json"
NATIVE_STATE_SHA256 = "9dc986c7b6c441e81cd6f7f57cc3801f4db43878ec55628b086eb9613108d1ac"
NATIVE_ADMISSION_FILE = "semantic_um_observe_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "eefdb484353da963ab6356e5a6819527bfb4b7a12263d33402edd2de997189bd"


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
