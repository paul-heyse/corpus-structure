"""Frozen test-architecture semantic-alignment source provenance.

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

revision = "semantic_test_arch_20261102"
down_revision = "semantic_bound_only_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_test_arch_20261102_native.json"
NATIVE_STATE_SHA256 = "5c4c0ac8696f7362d573dc066986d9334c8ea678dd3570170d1852b858f835a8"
NATIVE_ADMISSION_FILE = "semantic_test_arch_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "dec2c8f01ccb1ce80eba2491adb88a750684e6128b8b57fdcf8b302343f7f6d8"


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
