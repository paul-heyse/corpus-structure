"""Frozen source-bound provenance for the optional-support callback correction.

Native functions, support policy and validation epoch v5 remain unchanged. The
single descriptor transition retains the strict captured implementation identity.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pdf_callback_20261102"
down_revision = "semantic_pdf_support_20261102"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_callback_20261102_native.json"
NATIVE_STATE_SHA256 = "abed2441f4983c5731f786efe96b485f58f069327c1ca44794daa973c2d1276b"
NATIVE_ADMISSION_FILE = "semantic_pdf_callback_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "30e5650af9e6c2846c3531dd1ccac622bc570dbc01f9ac9666fd23df6996f310"


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
