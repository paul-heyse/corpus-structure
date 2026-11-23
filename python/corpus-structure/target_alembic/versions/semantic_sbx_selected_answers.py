"""Apply the frozen native candidate semantic_sbx_selected_answers."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_selected_answers"
down_revision = 'semantic_sbx_current_root'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_selected_answers_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "804a324d98a0216bdb1620e3b396816db0baf78a6054d1438e1ae1ca0360d02a"
NATIVE_STATE_FILE = "semantic_sbx_selected_answers_native.json"
NATIVE_STATE_SHA256 = "5e2715547db7612d9ba57f0e39385c744fe5ca66db9153f04963e96ac40e49b4"
NATIVE_ADMISSION_FILE = "semantic_sbx_selected_answers_admission.sql"
NATIVE_ADMISSION_SHA256 = "32ffa89bf26e4e2e00417be70bdce3fc5eb2ca83dc0d47a55d4dfa9a19699021"


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
