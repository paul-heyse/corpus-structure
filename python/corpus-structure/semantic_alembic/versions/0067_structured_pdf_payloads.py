"""Frozen structured PDF payload custody, typed identity and validation admission.

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

revision = "semantic_pdf_20261101"
down_revision = "semantic_pg_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_20261101_native.json"
NATIVE_STATE_SHA256 = "5378a3222e9374fe1c91e92280babfee22e15358c66a7247a6e5d11f66efe95d"
NATIVE_ADMISSION_FILE = "semantic_pdf_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "2276b2805bbd7c9ed1db75ec51e9aef999f888acd293ef51416ea320fc853cb7"

PHYSICAL_REFERENCE_FILE = "semantic_pdf_20261101_physical.sql"
PHYSICAL_REFERENCE_SHA256 = "9c83501e4f19af18858a82496a854addb7878b1a9813e5fb0eee5b3f09a4de49"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen structured PDF payload artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    reference = _read_artifact(PHYSICAL_REFERENCE_FILE, PHYSICAL_REFERENCE_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen structured PDF payload state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    with native_owner(op.get_bind(), "corpus_sem_publisher"):
        execute_native_sql(op.get_bind(), reference.decode())
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("structured PDF payload downgrade refused; rebuild owned realization")
