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
NATIVE_UPGRADE_SHA256 = "4b53c0c4e39382a16e0fc4f3848415fde723808b47e53e4335cc82629df63cfe"
NATIVE_STATE_FILE = "semantic_sbx_current_root_native.json"
NATIVE_STATE_SHA256 = "7bf3cda63692935acac7f2bef0075511d2c037f9fb5157aa5068110d620799df"
NATIVE_ADMISSION_FILE = "semantic_sbx_current_root_admission.sql"
NATIVE_ADMISSION_SHA256 = "9477d8bd9e8dc42e899e967feeb14eb6bfe6f4b13602e94d9eea0b00a237428c"


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
