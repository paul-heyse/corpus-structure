"""Dispatch native grading by immutable reference-set protocol; forward only."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_op_grade_20261105"
down_revision = "semantic_runtime_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_op_grade_20261105_native.json"
NATIVE_STATE_SHA256 = "0e980204c9dd6ca265f24380164412a78606bef0b645db435993b0f89fd2e9b3"
NATIVE_ADMISSION_FILE = "semantic_op_grade_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "ef91c7cc19dd625ea0096f138461aabee19644626bb3ee380c66c265df882627"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen operation-grade artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible operation-grade predecessor")
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive operation-grade downgrade refused")
