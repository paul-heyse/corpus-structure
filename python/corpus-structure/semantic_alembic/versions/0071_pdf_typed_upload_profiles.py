"""Frozen typed PDF upload profiles and unchanged-CHECK physical receipt.

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

revision = "semantic_pdf_budget_20261101"
down_revision = "semantic_pdf_adopt_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_budget_20261101_native.json"
NATIVE_STATE_SHA256 = "ebccd680e48d7674007b1dcdb8104c60d66272509d8fd783a8f74d62bf3deee7"
NATIVE_ADMISSION_FILE = "semantic_pdf_budget_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "e7f35b1e937c2899a086fa15b25ffb60a1ae3ce291fb4998840199dc08145865"

PHYSICAL_REFERENCE_FILE = "semantic_pdf_budget_20261101_physical.sql"
PHYSICAL_REFERENCE_SHA256 = "64f929af61527c6c68f0801a661b6e9a7630af1ec2c35aea9e0522d0aa20daea"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen typed PDF upload profile artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    reference = _read_artifact(PHYSICAL_REFERENCE_FILE, PHYSICAL_REFERENCE_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen typed PDF upload profile state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    with native_owner(op.get_bind(), "corpus_sem_publisher"):
        execute_native_sql(op.get_bind(), reference.decode())
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("typed PDF upload profile downgrade refused; rebuild owned realization")
