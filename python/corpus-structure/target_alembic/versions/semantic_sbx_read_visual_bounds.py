"""Apply the frozen native candidate semantic_sbx_read_visual_bounds."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_read_visual_bounds"
down_revision = 'semantic_sbx_pdf_report_address'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_read_visual_bounds_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "46b9337d1f0595211bef0653e5613737de5d4383e8cb0469e78cc86a29aacfdb"
NATIVE_STATE_FILE = "semantic_sbx_read_visual_bounds_native.json"
NATIVE_STATE_SHA256 = "c74200b6a47bf848e9e78d7634a3cb31649cc9a0c99ad5b3f127580c12608c74"
NATIVE_ADMISSION_FILE = "semantic_sbx_read_visual_bounds_admission.sql"
NATIVE_ADMISSION_SHA256 = "8522b9878487bcc8860a309c49e944c311f08a94e15d02629279f80baec00fe2"


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
