"""Strengthen contextual decision closure after local enrichment; forward only."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_guard_20261105"
down_revision = "semantic_pce_local_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_guard_20261105_native.json"
NATIVE_STATE_SHA256 = "f52502deb9f89f9d5b0dc2b4acbbbadecdab6728967c23d2facd68322e98b4e7"
NATIVE_ADMISSION_FILE = "semantic_pce_guard_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "d68bec63c72798a6ff5c5f30ef41675e017587fada7914cc60fec483895b894c"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen contextual guard artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible contextual guard predecessor")
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive contextual guard downgrade refused")
