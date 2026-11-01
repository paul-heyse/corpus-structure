"""Frozen multiplicity-preserving PDF ownership counts and revision-scoped membership.

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

revision = "semantic_pdf_owners_20261101"
down_revision = "semantic_pdf_access_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_owners_20261101_native.json"
NATIVE_STATE_SHA256 = "2d3a7f0f109241d6446527495453beed28590f3c7e052bf9aeccdd6c17980306"
NATIVE_ADMISSION_FILE = "semantic_pdf_owners_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "4b043f2c4a43106d8ff21dfff0862459b85e89bda3635cbcfd736cbecf1455c1"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen PDF ownership counts artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen PDF ownership counts state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("PDF ownership counts downgrade refused; rebuild owned realization")
