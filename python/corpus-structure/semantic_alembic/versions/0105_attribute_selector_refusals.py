"""Attribute assertion selectors use exact source custody; forward from frozen104."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ac_attribute_20261103"
down_revision = "semantic_ac_import_20261103"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_ac_attribute_20261103_native.json"
NATIVE_STATE_SHA256 = "60a62e68ab41ae62d9655832059c5115c236f6a30f9f27eb62bf5675a65d6215"
NATIVE_ADMISSION_FILE = "semantic_ac_attribute_20261103_admission.sql"
NATIVE_ADMISSION_SHA256 = "8882a585c5cbd15102fec87dca66d5e132921c19e259a4b1f7f31dd9cba6758d"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("native attribute artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible native attribute predecessor")
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive attribute downgrade refused; rebuild an owned database")
