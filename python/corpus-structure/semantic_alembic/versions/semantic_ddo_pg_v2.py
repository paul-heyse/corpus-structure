"""Apply the frozen native candidate semantic_ddo_pg_v2."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pg_v2"
down_revision = "semantic_ddo_pg_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pg_v2_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "05d246bb4a3715a76c93bd14b7408db56d37d77f7e8fcdcb18d49afe10ed7ce8"
NATIVE_STATE_FILE = "semantic_ddo_pg_v2_native.json"
NATIVE_STATE_SHA256 = "97fbbd61ada3f6ff47133b8845b1699a470e63a8a0711c9bbec8e02bfe8ef514"
NATIVE_ADMISSION_FILE = "semantic_ddo_pg_v2_admission.sql"
NATIVE_ADMISSION_SHA256 = "3e728c14d39fa3a1f8082e7c53dbef09ff2322226d25913866d54f99f0c25b13"


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
