"""Apply the frozen native candidate semantic_ddo_pe_n21."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n21"
down_revision = 'semantic_ddo_pe_n20'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n21_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d60a682cf3e5a8719f447a571130154f37a9d1a594967f2f6d9fac7adcc9379e"
NATIVE_STATE_FILE = "semantic_ddo_pe_n21_native.json"
NATIVE_STATE_SHA256 = "8cf2066aed10c05d0616732da634a8f5848bcd032d7e474ef1a349789d75c5c9"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n21_admission.sql"
NATIVE_ADMISSION_SHA256 = "a9bf558c3fd7a26586a946c3ebcd1e34a208aa01b6f0dcecc853dbc2605f00e2"


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
