"""Imported declaration-only membership with exact prior lineage; forward from frozen103."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ac_import_20261103"
down_revision = "semantic_ac_lineage_20261103"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_ac_import_20261103_native.json"
NATIVE_STATE_SHA256 = "a42da9c7b85f74d347d0b971eaf861e338d8e7bf436ae5fc2ae89174230ecc3d"
NATIVE_ADMISSION_FILE = "semantic_ac_import_20261103_admission.sql"
NATIVE_ADMISSION_SHA256 = "c6fa445285606b3a1a0e0ad678287f4b26d2a992d60dd2f6dc9916cea6445c2b"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("native import artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible native import predecessor")
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive import downgrade refused; rebuild an owned database")
