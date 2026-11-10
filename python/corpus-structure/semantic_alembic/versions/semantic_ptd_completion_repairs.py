"""Apply the frozen native candidate semantic_ptd_completion_repairs."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ptd_completion_repairs"
down_revision = "semantic_ptd_explanations"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ptd_completion_repairs_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "4ff5204763b863df8c7b6dcf90cf347bf88fa5cb386caa0e81ca1f7666f62422"
NATIVE_STATE_FILE = "semantic_ptd_completion_repairs_native.json"
NATIVE_STATE_SHA256 = "4ae3f9d7100b115d2255f639b3205de792fd8af9a3c5f9b6dd58e5b1ff64301b"
NATIVE_ADMISSION_FILE = "semantic_ptd_completion_repairs_admission.sql"
NATIVE_ADMISSION_SHA256 = "c51981c0e5fd0e1c3473d9bab561715d5d3159856b32d13b53ecec749c539a5d"


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
