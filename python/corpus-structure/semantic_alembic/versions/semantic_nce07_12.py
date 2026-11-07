"""Apply the frozen native candidate semantic_nce07_12."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce07_12"
down_revision = "semantic_nce06_heading_release"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce07_12_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "477b966c173df8ab5039c70659c15a2e4edc6abeeee091293e02da158a489f5f"
NATIVE_STATE_FILE = "semantic_nce07_12_native.json"
NATIVE_STATE_SHA256 = "7479be7c58bd3b7579ed62e83c8a7ab20053efb0697f16ccfa157fe1ce4b3c42"
NATIVE_ADMISSION_FILE = "semantic_nce07_12_admission.sql"
NATIVE_ADMISSION_SHA256 = "33446bc9a38749120f367902e487b4f24c729b600d03298ec147adba859b9b0f"


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
