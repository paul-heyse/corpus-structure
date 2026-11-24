"""Apply the frozen native candidate semantic_sbx_selected_pdf."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_selected_pdf"
down_revision = 'semantic_sbx_qualified_reads'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_selected_pdf_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "34f06a612682e0fcfe4d1c8e0a6730d838a89f5644adfdde87c37d700d94bd14"
NATIVE_STATE_FILE = "semantic_sbx_selected_pdf_native.json"
NATIVE_STATE_SHA256 = "74a9c24c2e38bb2a90e505d6cfe683200b6fcf0e0c1bacb5ad5eb863147be655"
NATIVE_ADMISSION_FILE = "semantic_sbx_selected_pdf_admission.sql"
NATIVE_ADMISSION_SHA256 = "0824afd5082808e7bc681c35bc11d94494de4fcc2b2421ee6bfcd19b1f9738f1"


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
