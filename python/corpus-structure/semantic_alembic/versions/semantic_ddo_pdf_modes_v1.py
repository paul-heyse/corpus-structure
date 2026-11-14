"""Apply the frozen native candidate semantic_ddo_pdf_modes_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pdf_modes_v1"
down_revision = "semantic_ddo_runtime_v3"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pdf_modes_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "f05a71b38d7c7b9e330c14ca808135613594e7f2b4ccfe3263cb82ed34ea4dd4"
NATIVE_STATE_FILE = "semantic_ddo_pdf_modes_v1_native.json"
NATIVE_STATE_SHA256 = "f5bb60c5e9f9b9f359952a05ac8ebd4458e777b22b6cf0092993df54c35bee4b"
NATIVE_ADMISSION_FILE = "semantic_ddo_pdf_modes_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "3948b4395438e6888f49b6f148033e2de96d71d3f67b57ca18ac5b7276a6d2ec"


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
