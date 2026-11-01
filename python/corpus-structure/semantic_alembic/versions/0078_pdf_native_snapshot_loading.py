"""Frozen profile-qualified native snapshot loading admission provenance.

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

revision = "semantic_pdf_snapshot_20261101"
down_revision = "semantic_grammar_20261101"
branch_labels = None
depends_on = None

NATIVE_STATE_FILE = "semantic_pdf_snapshot_20261101_native.json"
NATIVE_STATE_SHA256 = "f60c090063001cb81f1a623f2e8f579cda8cdf9903fb2ccabde1c5ddf49b8fbb"
NATIVE_ADMISSION_FILE = "semantic_pdf_snapshot_20261101_admission.sql"
NATIVE_ADMISSION_SHA256 = "2edb9c0709d28637e38465aabe34c50561e51be6c1498bf755679da31a6ec49b"


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native snapshot admission artifact differs: " + name)
    return content


def upgrade() -> None:
    # Verify every frozen input before the first native operation can affect the caller.
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen native snapshot admission state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    operations = Operations(op.get_context())
    for payload in state["operations"]:
        NativeTransitionOp.native_transition(operations, payload)
    admit_native(op.get_bind(), desired)


def downgrade() -> None:
    raise RuntimeError("native snapshot admission downgrade refused; rebuild owned realization")
