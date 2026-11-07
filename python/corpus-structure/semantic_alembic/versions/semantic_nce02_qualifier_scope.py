"""Apply the frozen native candidate semantic_nce02_qualifier_scope."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce02_qualifier_scope"
down_revision = "semantic_nce_evidence_guards"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce02_qualifier_scope_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "723924415488cda7875d388401ba06ca9a234af2ea2b8376d1247fc4814c8411"
NATIVE_STATE_FILE = "semantic_nce02_qualifier_scope_native.json"
NATIVE_STATE_SHA256 = "5dfbb1013bcb0f5ab6af4f287ea2eb3dcd2fe8ecbc678af50deebd2633d39974"
NATIVE_ADMISSION_FILE = "semantic_nce02_qualifier_scope_admission.sql"
NATIVE_ADMISSION_SHA256 = "209cf90787b5a678400f33a3e8292697efe8de424c4129b9b7a0382536011f2f"


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
