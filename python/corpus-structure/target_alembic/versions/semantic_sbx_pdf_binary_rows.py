"""Apply the frozen native candidate semantic_sbx_pdf_binary_rows."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_pdf_binary_rows"
down_revision = 'semantic_sbx_read_visual_bounds'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_pdf_binary_rows_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "b87f8395de170741bd132e35420564a5853b2dd05f3fe49d78b0b4668f1a9584"
NATIVE_STATE_FILE = "semantic_sbx_pdf_binary_rows_native.json"
NATIVE_STATE_SHA256 = "76ccad66aac1b1be257ea90b58aca551724debd670151b6eb59d00fd32ad44ff"
NATIVE_ADMISSION_FILE = "semantic_sbx_pdf_binary_rows_admission.sql"
NATIVE_ADMISSION_SHA256 = "23cc73ce19734c34a9d35cce3f83c74cc3530e97d4ce816dae0e9d1edd2fe7e9"


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
