"""Apply the frozen native candidate semantic_ddo_explicit_pin_scope."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_explicit_pin_scope"
down_revision = 'semantic_ddo_capture_lineage'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_explicit_pin_scope_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "57abb44b34228f0c51d5e68059da8bea3c848b7120f13533f6572d9000185cb7"
NATIVE_STATE_FILE = "semantic_ddo_explicit_pin_scope_native.json"
NATIVE_STATE_SHA256 = "6d65597443a4902a514769179cc05ce7f854b8bea4f338893264d84a543e71c3"
NATIVE_ADMISSION_FILE = "semantic_ddo_explicit_pin_scope_admission.sql"
NATIVE_ADMISSION_SHA256 = "a96eda39f50e65df86ebf365d6523f2a05c5a099a0b30d9f79e13ad648ba2328"


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
        admit_privileges(op.get_bind(), state["privileges"])


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
