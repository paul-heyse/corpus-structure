"""Apply the frozen native candidate semantic_chandra_pdf_exact."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_chandra_pdf_exact"
down_revision = "semantic_chandra_pdf_checks"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_chandra_pdf_exact_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "a95de620fb8d6e7f84c70bc39a2a30097fb3cb4334826e3733445adb0796fbf5"
NATIVE_STATE_FILE = "semantic_chandra_pdf_exact_native.json"
NATIVE_STATE_SHA256 = "9abde5c9a16c6c61ec0cf90b15aabf875fe6e5f0ff2f6d633bc407c1350a914e"
NATIVE_ADMISSION_FILE = "semantic_chandra_pdf_exact_admission.sql"
NATIVE_ADMISSION_SHA256 = "48eb50944af68842568948a0d35ff107ae8b2020b2c7bd403bdbeee20fb2b952"


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
