"""Frozen PDF streaming publication and execution ABI 20 admission.

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

revision = "semantic_pdf_stream_20261101"
down_revision = "semantic_pdf_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_stream_20261101_native.json"
NATIVE_STATE_SHA256 = "18722bf082d1812600d60251a3028098518032e04f164f43193e2e3332c7aeb6"
NATIVE_ADMISSION_FILE = "semantic_pdf_stream_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "eddd2eb5d3751ee946f972081394690c6f4f3b5cf4914f9bb696c213489986e4"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen PDF streaming publication artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen PDF streaming publication state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("PDF streaming publication downgrade refused; rebuild owned realization")
