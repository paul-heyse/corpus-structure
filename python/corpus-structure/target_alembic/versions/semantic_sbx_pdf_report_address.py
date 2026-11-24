"""Apply the frozen native candidate semantic_sbx_pdf_report_address."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_pdf_report_address"
down_revision = 'semantic_sbx_selected_pdf'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_pdf_report_address_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "ed0c321ef824e769e299ebaf25f4ee2c01f2526bc280684394eea5cff73f7089"
NATIVE_STATE_FILE = "semantic_sbx_pdf_report_address_native.json"
NATIVE_STATE_SHA256 = "29b91a8f59dd88757166c2a451907b8791dcd7a7eaf58bb069484dfdd31c936f"
NATIVE_ADMISSION_FILE = "semantic_sbx_pdf_report_address_admission.sql"
NATIVE_ADMISSION_SHA256 = "4fcad17562d4d644971f21d2c1a02d63768ed2f7fc3ffe8bc754aee3236966f3"


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
