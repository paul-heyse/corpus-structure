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
NATIVE_UPGRADE_SHA256 = "e68a38768a7bb9e302373f925b96c8daae64277e9c2823123cfec728abb1dd2c"
NATIVE_STATE_FILE = "semantic_sbx_current_root_native.json"
NATIVE_STATE_SHA256 = "bec6f4c17634fdffb65e229d17df878536069cd3eed03fdb4d70531c35725822"
NATIVE_ADMISSION_FILE = "semantic_sbx_current_root_admission.sql"
NATIVE_ADMISSION_SHA256 = "7fc4eee3ea26f9fea444dc77de34aa4eb25938ab7ab7579aac6982f6fd1f01f2"


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
