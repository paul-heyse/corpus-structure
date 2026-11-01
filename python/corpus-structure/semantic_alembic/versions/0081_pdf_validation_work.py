"""Frozen PDF validation work, native capture and integrated metadata policy.

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

revision = "semantic_pdf_validate_20261101"
down_revision = "semantic_pdf_evidence_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_validate_20261101_native.json"
NATIVE_STATE_SHA256 = "68854e0eb001c23f2e9dde7de8e3cbaf9a649b647b0da2866843824d2a4814b8"
NATIVE_ADMISSION_FILE = "semantic_pdf_validate_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "e8c597bf9acbb53e467fd8191844acc9f6b8e69daa255768c86006f178f61891"

PHYSICAL_REFERENCE_FILE = "semantic_pdf_validate_20261101_physical.sql"
PHYSICAL_REFERENCE_SHA256 = "3a181abee4ddee5b311b79519577d23fd74a4ff04ed02e287f71ef6743d9dfb0"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen PDF validation work policy artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    reference = _read_artifact(PHYSICAL_REFERENCE_FILE, PHYSICAL_REFERENCE_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen PDF validation work policy state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    with native_owner(op.get_bind(), "corpus_sem_publisher"):
        execute_native_sql(op.get_bind(), reference.decode())
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("PDF validation work policy downgrade refused; rebuild owned realization")
