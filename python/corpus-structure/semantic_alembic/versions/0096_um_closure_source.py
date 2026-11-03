"""Frozen unified-model operation and analysis source provenance.

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

revision = "semantic_um_closure_20261102"
down_revision = "semantic_test_arch_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_um_closure_20261102_native.json"
NATIVE_STATE_SHA256 = "b4795e840cb442fcc556797a41b12f0b3a807ecdf6c6fc856035493bc18c9325"
NATIVE_ADMISSION_FILE = "semantic_um_closure_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "5a9500b1ed49b391f8eb942c50f7013e2c02d397b75fbd661f1ae49a7bc44310"


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
