"""Apply the frozen native candidate semantic_ddo_consumer_fixes."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_consumer_fixes"
down_revision = 'semantic_ddo_compiler23'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_consumer_fixes_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "bb750ff28a21c66bbc8db0af692296aa69d26301b7ce3e6caeb7cdf9557d5399"
NATIVE_STATE_FILE = "semantic_ddo_consumer_fixes_native.json"
NATIVE_STATE_SHA256 = "20826dd5b648071516244290fcef60fd4c5b8c8f81779a886504edb3bd0cfd6f"
NATIVE_ADMISSION_FILE = "semantic_ddo_consumer_fixes_admission.sql"
NATIVE_ADMISSION_SHA256 = "8963694ab9e6e30d894206e606ae4beaf341a59ba2b0b734d1e47628dad5f343"


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
