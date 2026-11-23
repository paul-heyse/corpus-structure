"""Apply the frozen native candidate semantic_sbx_current_root."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_current_root"
down_revision = None
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_current_root_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "15be55bdb612b48003db55774047e55748ae40f47bd1a5d1f46b76f850cbca21"
NATIVE_STATE_FILE = "semantic_sbx_current_root_native.json"
NATIVE_STATE_SHA256 = "d155ebe7276605c600008a51a6a1a9a774699deeba9001a9f568a66ed9ceb448"
NATIVE_ADMISSION_FILE = "semantic_sbx_current_root_admission.sql"
NATIVE_ADMISSION_SHA256 = "0a170021d7e96e34f3c090dbe1afdeba6f8c198eed55ff7e30173878bb4b11bc"


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
        admit_privileges(
            op.get_bind(), state["privileges"],
            purpose_roles=state.get("privilege_purpose_roles"),
        )


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
