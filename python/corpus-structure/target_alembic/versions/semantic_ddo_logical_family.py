"""Apply the frozen native candidate semantic_ddo_logical_family."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_logical_family"
down_revision = 'semantic_ddo_explicit_pin_scope'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_logical_family_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "b752e6f2c81091c402fdd1d7339f146a0494300a8da02e9572cb615706919d97"
NATIVE_STATE_FILE = "semantic_ddo_logical_family_native.json"
NATIVE_STATE_SHA256 = "c8d408f18fd82547ca1fc08318d9b1c2ee6f32c773200ffee58f46022d51623f"
NATIVE_ADMISSION_FILE = "semantic_ddo_logical_family_admission.sql"
NATIVE_ADMISSION_SHA256 = "dead9b329d37f2de94be492c6da1f685902ef977acce286e36bda1b02a3ba2fe"


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
