"""Apply the frozen native candidate semantic_chandra_pdf_checks."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_chandra_pdf_checks"
down_revision = "semantic_chandra_grouped_fix"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_chandra_pdf_checks_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d606c01cecb89e6e48b39bd3b93668e60b5675c118a68f73d0316d2efbbedaad"
NATIVE_STATE_FILE = "semantic_chandra_pdf_checks_native.json"
NATIVE_STATE_SHA256 = "5116e20abcc98d8394d86421ec9a799714e115105a2f4487c2b569f9fa9373a3"
NATIVE_ADMISSION_FILE = "semantic_chandra_pdf_checks_admission.sql"
NATIVE_ADMISSION_SHA256 = "fd8b5c52a1ff6629c1121ce3b9819f69396f64573c7b4f2be6a8a270970e44fb"


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
