"""Apply the frozen native candidate semantic_ddo_facts_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_facts_v1"
down_revision = "semantic_ddo_drole_v2"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_facts_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d7e5e21e3b03dffaaa893843d9d9d55832a0b585b5356a24811a348db97ddd51"
NATIVE_STATE_FILE = "semantic_ddo_facts_v1_native.json"
NATIVE_STATE_SHA256 = "da3a8dec91207b7d57875ea32f566d32e5b8faa37085d0f491328721615affcf"
NATIVE_ADMISSION_FILE = "semantic_ddo_facts_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "53a599684b9418f57688a1c6884d4c2b85e5833010b56ba901f826af9b188ae6"


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
