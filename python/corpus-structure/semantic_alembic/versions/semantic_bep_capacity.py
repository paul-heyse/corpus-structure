"""Apply the frozen native candidate semantic_bep_capacity."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_bep_capacity"
down_revision = "semantic_tc10_task_semantics"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_bep_capacity_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "9323011195655dd64690313126289c8b26dd68c6ab68a8285a5d3647072d623f"
NATIVE_STATE_FILE = "semantic_bep_capacity_native.json"
NATIVE_STATE_SHA256 = "c9863220b13ccca83496bc1dcf2ce39f10998c2592700b062494210a88ff631d"
NATIVE_ADMISSION_FILE = "semantic_bep_capacity_admission.sql"
NATIVE_ADMISSION_SHA256 = "68fb91dc0c0f5abe1cc7b0ce95fc3ac8e7d7378614b263dff9e15797d4830e1d"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
