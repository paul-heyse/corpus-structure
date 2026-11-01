"""Frozen PDF projection isolation and finalized-validation receipt policy.

Only explicit native transitions execute; historical table snapshots remain immutable.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import (
    NativeObject,
    admit_native,
    execute_native_sql,
    native_owner,
)

revision = "semantic_pdf_receipt_20261101"
down_revision = "semantic_pdf_owners_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_receipt_20261101_native.json"
NATIVE_STATE_SHA256 = "b5e5e2b9d9a666b6cc5b91fa0ea810496c91e4744688095fb87b72d54ca5e202"
NATIVE_ADMISSION_FILE = "semantic_pdf_receipt_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "7847d74618bb0a445ae31bb63c4dd042c96cf26425843fd049c1aacf7eeec59d"

PHYSICAL_REFERENCE_FILE = "semantic_pdf_receipt_20261101_physical.sql"
PHYSICAL_REFERENCE_SHA256 = "bb07f344acdb5b87f5150f41205bd9ed2fcf0f675edef1067303c5b0c4a63b3a"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen PDF projection receipt policy artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    reference = _read_artifact(PHYSICAL_REFERENCE_FILE, PHYSICAL_REFERENCE_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen PDF projection receipt policy state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    with native_owner(op.get_bind(), "corpus_sem_publisher"):
        execute_native_sql(op.get_bind(), reference.decode())
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("PDF projection receipt policy downgrade refused; rebuild owned realization")
