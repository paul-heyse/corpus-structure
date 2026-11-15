"""Apply the frozen native candidate semantic_ddo_pg_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pg_v1"
down_revision = "semantic_ddo_context_pdf_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pg_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "1551b416d14aff58cbbf44f3f2dfe2e664e76eb3e8ecb1c31a9f840394f7fe77"
NATIVE_STATE_FILE = "semantic_ddo_pg_v1_native.json"
NATIVE_STATE_SHA256 = "fdfd980bf7a7457d3972216dd2071354fa231e87a2af9347cc15130fd7f19d79"
NATIVE_ADMISSION_FILE = "semantic_ddo_pg_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "f1a4b5ec94b95139fbdbb0654db6c89a59a2321a7750cea21b6d2ca341082ea3"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] not in {1, 2} or state["predecessor"] != down_revision:
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
