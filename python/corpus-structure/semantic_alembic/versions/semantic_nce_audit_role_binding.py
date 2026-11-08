"""Apply the frozen native candidate semantic_nce_audit_role_binding."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_audit_role_binding"
down_revision = "semantic_nce_audit_helpers"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_audit_role_binding_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "0776faaab73a07e1a1abff19b00299862732f5f494a79691e9c70d8f998c510e"
NATIVE_STATE_FILE = "semantic_nce_audit_role_binding_native.json"
NATIVE_STATE_SHA256 = "bb12395cbfa35feb724d869cea9bef1cbff4cb8307e9c9344987eb9b15a3e862"
NATIVE_ADMISSION_FILE = "semantic_nce_audit_role_binding_admission.sql"
NATIVE_ADMISSION_SHA256 = "0616182f426d84dbd2d17475334271524cda0e271b14f9d27b13f78009825c90"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
