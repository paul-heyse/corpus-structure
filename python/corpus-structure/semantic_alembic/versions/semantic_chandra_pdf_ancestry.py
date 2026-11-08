"""Apply the frozen native candidate semantic_chandra_pdf_ancestry."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_chandra_pdf_ancestry"
down_revision = "semantic_chandra_pdf_exact"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_chandra_pdf_ancestry_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "9df8e6b6a1bf57ffc133b16af734b5fd83d8f84b7b50f6f099c3487825d818c4"
NATIVE_STATE_FILE = "semantic_chandra_pdf_ancestry_native.json"
NATIVE_STATE_SHA256 = "6df268d3cc1f9418f5b7eeeea3ed7c1fb252cfed07cf6b692dd17dfdc3b39ac3"
NATIVE_ADMISSION_FILE = "semantic_chandra_pdf_ancestry_admission.sql"
NATIVE_ADMISSION_SHA256 = "3c46a3b5bfa978e22e4918aa824d417d79ab2e97639595631221333f29e9d013"


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
