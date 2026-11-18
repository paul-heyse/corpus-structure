"""Apply the frozen native candidate semantic_ddo_pe_n15."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n15"
down_revision = 'semantic_ddo_pe_n14'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n15_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "aa6774fb316ca57e0c9e082d6bee212113476c6f9ef61fdf6f032cddfd4e451e"
NATIVE_STATE_FILE = "semantic_ddo_pe_n15_native.json"
NATIVE_STATE_SHA256 = "85caad60eaeba264074debff26683d147159f74704a8e373ee7ac94755e95498"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n15_admission.sql"
NATIVE_ADMISSION_SHA256 = "1c46bb29292287e3afc1a6bd850f1a0ecf19c09eb5a3c550ddafb35f3e701cd5"


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
