"""Frozen explicit native retirement admission provenance.

The admission SQL witnesses the explicit descriptor correction; its CREATE executes
through the frozen native payload, once. All artifacts are
byte-bound before effects and desired properties are admitted on the caller Connection.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pdf_retire_20261101"
down_revision = "semantic_pdf_validate_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_retire_20261101_native.json"
NATIVE_STATE_SHA256 = "cb9a1457f9e51dd71cd8b96642ff6e14835eea4dd2d9bcb19a245beccc321407"
NATIVE_ADMISSION_FILE = "semantic_pdf_retire_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "d743ec7be989cb527e58e8ab550673de5f879a6cbf3634d9bd274c2edf5bfb46"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen explicit native retirement admission artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen explicit native retirement admission state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError(
        "explicit native retirement admission downgrade refused; rebuild owned realization"
    )
