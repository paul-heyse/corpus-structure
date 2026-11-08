"""Apply the frozen native candidate semantic_nce_audit_governors."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_audit_governors"
down_revision = "semantic_nce_audit_role_binding"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_audit_governors_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "493c9cfc454e5032cc1a0d11f79defd7b0afd6ff4269e30dc20548d959fe56fb"
NATIVE_STATE_FILE = "semantic_nce_audit_governors_native.json"
NATIVE_STATE_SHA256 = "c929b58ae4dae9bba22bea8257874bd3927baaa1f8f87c04fb19eb0de1c9adbc"
NATIVE_ADMISSION_FILE = "semantic_nce_audit_governors_admission.sql"
NATIVE_ADMISSION_SHA256 = "3ad2b45ae5e6cd9913d477696f5e05ff28a1554f6d40d6cefc9a2917b1878bfc"


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
