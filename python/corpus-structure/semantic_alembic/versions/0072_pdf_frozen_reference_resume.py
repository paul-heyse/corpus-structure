"""Frozen set-based PDF reference preparation and state-preserving frozen resume.

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

revision = "semantic_pdf_resume_20261101"
down_revision = "semantic_pdf_budget_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_resume_20261101_native.json"
NATIVE_STATE_SHA256 = "7c39a3133ca629c6d1cae3ca56e996ad008b3b338e1bd97d92141030eeb9c9ed"
NATIVE_ADMISSION_FILE = "semantic_pdf_resume_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "616d242e4ab78ccbacae20738dbff014789dc695e1906762cd3d37779a3577c4"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen PDF frozen preparation/resume artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen PDF frozen preparation/resume state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("PDF frozen preparation/resume downgrade refused; rebuild owned realization")
