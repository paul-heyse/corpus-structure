"""Owned linguistic products and same-view source dependencies; forward from frozen105."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_m1_preparation_20261104"
down_revision = "semantic_ac_attribute_20261103"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_m1_preparation_20261104_native.json"
NATIVE_STATE_SHA256 = "ec3cd84261de6d3f4d9c5765be898b0c8e4ce9565d524e3d2ab386b34377ed97"
NATIVE_ADMISSION_FILE = "semantic_m1_preparation_20261104_admission.sql"
NATIVE_ADMISSION_SHA256 = "e467dd3715b3068fdca6bebcbcb0f5a79a1629da600d287cc8710d8422a1ae62"
PHYSICAL_STATE_FILE = "semantic_m1_preparation_20261104_physical.sql"
PHYSICAL_STATE_SHA256 = "d6440f8ff85cc767102f37ca33760d8ef988fd1675d6ceac8ecc38860373323e"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("M1 preparation artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    physical = _read(PHYSICAL_STATE_FILE, PHYSICAL_STATE_SHA256).decode()
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible M1 preparation predecessor")
    original_role = op.get_bind().exec_driver_sql("SELECT current_user").scalar_one()
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.execute(physical)
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(original_role))
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive M1 preparation downgrade refused; rebuild owned storage")
