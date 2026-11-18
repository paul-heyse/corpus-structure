"""Apply the frozen native candidate semantic_ddo_pe_n7."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n7"
down_revision = 'semantic_ddo_pe_n6'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n7_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "22c40b24ec7e45d12fe59b5099f6afd039e12b4cabbb993550cd8bdf811da354"
NATIVE_STATE_FILE = "semantic_ddo_pe_n7_native.json"
NATIVE_STATE_SHA256 = "9463bbee40d1db75027ffdff3f57e59198d9c3d716ab8d0f6a88bdecab84feea"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n7_admission.sql"
NATIVE_ADMISSION_SHA256 = "82a683f0f8adca98a233968f976103f425db09e9fae67ddd4e68b0e3e7a0ee94"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 2 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))
    if state["version"] == 2:
        from corpus_structure.semantic.alembic_privileges import admit_privileges
        admit_privileges(op.get_bind(), state["privileges"])


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
