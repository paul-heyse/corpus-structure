"""Apply the frozen native candidate semantic_ddo_pe_n24."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n24"
down_revision = 'semantic_ddo_pe_n23'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n24_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "333db5d8e090b61bb0fa7073a025493b021f7dbc3d172f46e565f885e003313c"
NATIVE_STATE_FILE = "semantic_ddo_pe_n24_native.json"
NATIVE_STATE_SHA256 = "1239304d14c0564f4ccaeea1d6ce922ecc6d78a7720d94d899424c498a6f01c1"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n24_admission.sql"
NATIVE_ADMISSION_SHA256 = "33fd3b9e3fdbf8dd708ad35f899fc2d32dc55453a3ea00cb6db4331d214284e7"


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
        admit_privileges(op.get_bind(), state["privileges"])


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
