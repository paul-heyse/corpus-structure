"""Apply the frozen native candidate semantic_chandra_grouped_fix."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_chandra_grouped_fix"
down_revision = "semantic_chandra_grouped"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_chandra_grouped_fix_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "aed5d815182fe4ccf09cfb61649206c6200e646ad2bb13687797148a4bc7c42c"
NATIVE_STATE_FILE = "semantic_chandra_grouped_fix_native.json"
NATIVE_STATE_SHA256 = "2796f0afc22e8ba9107e13a3d7c4118d294f7bf779617380f055ade09aed15c0"
NATIVE_ADMISSION_FILE = "semantic_chandra_grouped_fix_admission.sql"
NATIVE_ADMISSION_SHA256 = "14f6acc11794a6df3afb7c510310910c8ffb4992c3d7324d56cc95d8a6ecd238"


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
