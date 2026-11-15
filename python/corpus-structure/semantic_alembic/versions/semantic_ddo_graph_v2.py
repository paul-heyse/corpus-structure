"""Apply the frozen native candidate semantic_ddo_graph_v2."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_graph_v2"
down_revision = "semantic_ddo_graph_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_graph_v2_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "2a799600d4cb1bf4e0058fc0604aba0b01d604af948cde940422dd473b950a45"
NATIVE_STATE_FILE = "semantic_ddo_graph_v2_native.json"
NATIVE_STATE_SHA256 = "949ad35055dfd850faeee47bec8478360e0a5cf5b01178849dffa8d6fe9671e9"
NATIVE_ADMISSION_FILE = "semantic_ddo_graph_v2_admission.sql"
NATIVE_ADMISSION_SHA256 = "ff85f87cf8da71c7495836a3c2f0818867c4d34b661f094f4b876571677f612d"


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
