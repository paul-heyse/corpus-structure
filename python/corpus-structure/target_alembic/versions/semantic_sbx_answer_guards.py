"""Apply the frozen native candidate semantic_sbx_answer_guards."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_answer_guards"
down_revision = 'semantic_sbx_selected_answers'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_answer_guards_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "f3e7614189c7f3efbc15571a129c0eda3b7f33b12930e4ded2a82e5512107706"
NATIVE_STATE_FILE = "semantic_sbx_answer_guards_native.json"
NATIVE_STATE_SHA256 = "f43d3d27e0ee9c11dd4ba806c30d09e462b01530b9c7b7973edd680e9d46062d"
NATIVE_ADMISSION_FILE = "semantic_sbx_answer_guards_admission.sql"
NATIVE_ADMISSION_SHA256 = "e783c95d78623a80642a38e35ff9252b5923da57a8dca484ee7e6736c93c5d9c"


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
