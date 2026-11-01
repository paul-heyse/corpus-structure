"""Frozen PostgreSQL capability projections and execution ABI 18 admission.

The admission SQL is the reviewed source witness for the two admission operations;
those CREATEs execute through their frozen native payloads, once. All artifacts are
byte-bound before effects and desired properties are admitted on the caller Connection.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pg_20261101"
down_revision = "semantic_0065"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pg_20261101_native.json"
NATIVE_STATE_SHA256 = "da7c92380769181965bd276adf1ef4ffd22373937d68c0221937e6d154a304f4"
NATIVE_ADMISSION_FILE = "semantic_pg_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "37bf4a42a8d59b72a944c819a52edd34d560ae0b1fcb61e4d5c0904794557692"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen PostgreSQL capability artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen PostgreSQL capability state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("PostgreSQL capability downgrade refused; rebuild owned realization")
