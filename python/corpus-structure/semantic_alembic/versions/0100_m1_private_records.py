"""Frozen authenticated private source-record custody and exact implementation binding.

Only private candidate envelopes are admitted. Accepted whole-record publication
and field-addressable public relations remain outside this native revision.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_private_20261103"
down_revision = "semantic_um_section_20261103"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_m1_private_20261103_native.json"
NATIVE_STATE_SHA256 = "35d13761e346a0bf861f1b29fda2c9db4fe186215e6f0e3a7242514fe793be60"
NATIVE_ADMISSION_FILE = "semantic_m1_private_20261103_admission.sql"
NATIVE_ADMISSION_SHA256 = "ebcd66ebe6f8c100ff24d14e0ac57836c56fbdfdf51c0413ae1ee17bd1a41383"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen M1 private record artifact differs: " + name)
    return content


def upgrade() -> None:
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen M1 private record state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    transitions = tuple(NativeTransitionOp.from_payload(item) for item in state["operations"])
    operations = Operations(op.get_context())
    for transition in transitions:
        operations.invoke(transition)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("M1 private record downgrade refused; rebuild owned realization")
