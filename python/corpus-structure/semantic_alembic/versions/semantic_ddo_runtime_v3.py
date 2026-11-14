"""Apply the frozen native candidate semantic_ddo_runtime_v3."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_runtime_v3"
down_revision = "semantic_ddo_external_v2"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_runtime_v3_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "f133266e65f1f9d45ca7fbdc4b4de98b361726866cc89089083a0f40e27bb965"
NATIVE_STATE_FILE = "semantic_ddo_runtime_v3_native.json"
NATIVE_STATE_SHA256 = "a419cb19a0637779364f02ce74daf1ab4d2d634bb7277aad89f387fd95a0987d"
NATIVE_ADMISSION_FILE = "semantic_ddo_runtime_v3_admission.sql"
NATIVE_ADMISSION_SHA256 = "47e57cf4e4917065b30186dafb42097dbc3e03d905388484ef5b5205e3eb9b82"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] not in {1, 2} or state["predecessor"] != down_revision:
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
