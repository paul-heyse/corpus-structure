"""Frozen compiler-23 call custody and protected run-scoped directions.

The context reader selects its family and page before decoding. Mixed native
profiles are preflighted before effects on the caller-owned transaction; old
frozen revisions and published products retain their original bytes.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_um_core_20261102"
down_revision = "semantic_um_observe_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_um_core_20261102_native.json"
NATIVE_STATE_SHA256 = "953da1fb9464c39c7cf7b3c91d9c8a1b106d04df9d2871f91c7108e20f6032c2"
NATIVE_ADMISSION_FILE = "semantic_um_core_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "48b03b2573f66f25df5f92c6c8ce1ed743951a46ddce5bb92bab9b37bf3641eb"


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
