"""Apply the frozen native candidate semantic_ddo_context_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_context_v1"
down_revision = "semantic_ddo_stream_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_context_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "cd2d7f631be648d3f11d39fdef9950ac77102cba8748f2bb83b888228993e478"
NATIVE_STATE_FILE = "semantic_ddo_context_v1_native.json"
NATIVE_STATE_SHA256 = "250c86932fad9f62d8dfe160362848a854a216d79ee2aa2be0fa4740bef12f77"
NATIVE_ADMISSION_FILE = "semantic_ddo_context_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "8cc5fddbca308496f48e3cf094812351a222a281f5180c67e52966a3ae8deb9d"


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
