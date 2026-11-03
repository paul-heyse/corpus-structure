"""Frozen selected section closure source provenance.

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

revision = "semantic_um_section_20261103"
down_revision = "semantic_um_selector_20261103"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_um_section_20261103_native.json"
NATIVE_STATE_SHA256 = "2de216f2df672947975ae061938536f84e14f05460feff28bc382c617389b2be"
NATIVE_ADMISSION_FILE = "semantic_um_section_20261103_admission.sql"
NATIVE_ADMISSION_SHA256 = "8790d507454c02814d7d378757ea19c5caaeda82acfbd15802f311a649ca1f36"


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
