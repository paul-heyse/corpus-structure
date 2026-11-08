"""Apply the frozen native candidate semantic_nce_audit_helpers."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_audit_helpers"
down_revision = "semantic_nce_audit_remaining"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_audit_helpers_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "09fbb0031d4e7014f9dc925fd5d7d66b0ccc8ae7d9071a4d5bedcc9b77f71546"
NATIVE_STATE_FILE = "semantic_nce_audit_helpers_native.json"
NATIVE_STATE_SHA256 = "e71fc10b5ee2f3da546c76e4f4e798221f77c724bea459d831917f6920f87b5b"
NATIVE_ADMISSION_FILE = "semantic_nce_audit_helpers_admission.sql"
NATIVE_ADMISSION_SHA256 = "732f0ff5694e4854f7c1a078c799673e4031d7ea49609949c3c67c7fa62e6890"


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
