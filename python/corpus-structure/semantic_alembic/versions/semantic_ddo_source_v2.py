"""Apply the frozen native candidate semantic_ddo_source_v2."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_source_v2"
down_revision = "semantic_ddo_source_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_source_v2_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "3ca3b1a55495872a1ab9c63710b4abe9530a9da6f81afb22dd1f86e8cd819c76"
NATIVE_STATE_FILE = "semantic_ddo_source_v2_native.json"
NATIVE_STATE_SHA256 = "87dbcf9f2df9ede9052c93cbfbe9f6a65d95c316f35974a47803c7ff24180179"
NATIVE_ADMISSION_FILE = "semantic_ddo_source_v2_admission.sql"
NATIVE_ADMISSION_SHA256 = "ae4304d7c2c4d08fb5f638f02a3cde5223b58621d75bfad2ac538bb50bf2b1c3"


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
