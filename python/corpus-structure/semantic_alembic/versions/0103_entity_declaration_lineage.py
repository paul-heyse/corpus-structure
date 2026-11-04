"""Declared entity membership and attributed source validation; forward from frozen102."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ac_lineage_20261103"
down_revision = "semantic_audit_closure_20261103"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_ac_lineage_20261103_native.json"
NATIVE_STATE_SHA256 = "6fc99060f6a946985f16c0fa035ecd9dc2533c94f6b5ac33eeb9a8154200c8c3"
NATIVE_ADMISSION_FILE = "semantic_ac_lineage_20261103_admission.sql"
NATIVE_ADMISSION_SHA256 = "f44d5b62e9817a51531b67043a7ff69cee3b41cebbfc376f894c57978b2fb219"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("native lineage artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible native lineage predecessor")
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive lineage downgrade refused; rebuild an owned database")
