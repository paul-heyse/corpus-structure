"""Frozen unified operation bindings, published addresses and native SQL body profiles.

Ordinary Alembic DDL preserves exact published pins through the placement backfill.
Native v1/v2 payloads and every artifact are validated before the first effect;
deployment uses these frozen bytes on the caller-owned connection and transaction.
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

revision = "semantic_um_model_20261102"
down_revision = "semantic_pdf_retire_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_um_model_20261102_native.json"
NATIVE_STATE_SHA256 = "0ad204348cb7b2ae1858e95b6bacf7b3fb31fecd4149a3627e3d4949cd63e373"
ORDINARY_FILE = "semantic_um_model_20261102_ordinary.sql"
ORDINARY_SHA256 = "5cbd6d65aaad7b16825f57cbe48a338cc10d669e6f64ac8b0fcf0f37a556a7f7"
PHYSICAL_REFERENCE_FILE = "semantic_um_model_20261102_physical.sql"
PHYSICAL_REFERENCE_SHA256 = "564845a57a74e813e2da98499d32494f2fbcf3c092b2558d7eb1565a34a7e039"
NATIVE_ADMISSION_FILE = "semantic_um_model_20261102_admission.sql"
NATIVE_ADMISSION_SHA256 = "501000228c2070b720a27fce878d95bc7b3a9cb8ec92b30c1ac1715321355267"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen unified domain model artifact differs: " + name)
    return content


def upgrade() -> None:
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    ordinary = _read_artifact(ORDINARY_FILE, ORDINARY_SHA256)
    reference = _read_artifact(PHYSICAL_REFERENCE_FILE, PHYSICAL_REFERENCE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen unified domain model state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    # Validate ALL mixed-version directives before ordinary DDL, never one at a time
    # after a preceding directive has already changed the caller's realization.
    transitions = tuple(NativeTransitionOp.from_payload(item) for item in state["operations"])
    connection = op.get_bind()
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, ordinary.decode())
        execute_native_sql(connection, reference.decode())
    operations = Operations(op.get_context())
    for transition in transitions:
        operations.invoke(transition)
    admit_native(connection, desired)


def downgrade() -> None:
    raise RuntimeError("unified domain model downgrade refused; rebuild owned realization")
