"""Apply the frozen native candidate semantic_nce_audit_finalize."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_audit_finalize"
down_revision = "semantic_nce_audit_fit_guard"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_audit_finalize_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d7a69369dea6c4e0942847fb40efcaab7875ce8fd3da1fd71892c33ace889439"
NATIVE_STATE_FILE = "semantic_nce_audit_finalize_native.json"
NATIVE_STATE_SHA256 = "b7d802d09f1ab94a7ecb97fb6d3399d2fe5e19a8854d758e861154683b6cf6bf"
NATIVE_ADMISSION_FILE = "semantic_nce_audit_finalize_admission.sql"
NATIVE_ADMISSION_SHA256 = "4623db1508a00e008657954e7343a3dd291b117f7311352e0975fde65dbfc79a"


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
