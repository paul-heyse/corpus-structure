"""Apply the frozen native candidate semantic_ddo_pe_n12."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n12"
down_revision = 'semantic_ddo_pe_n11'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n12_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "0328a237c5b56a499301c2db06fa083c47b54c88ca8bf4949c0f3604b53d98bb"
NATIVE_STATE_FILE = "semantic_ddo_pe_n12_native.json"
NATIVE_STATE_SHA256 = "66525041107b68bdc7d115522e0fd7a276e5600e408675f33b6404bbc786699f"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n12_admission.sql"
NATIVE_ADMISSION_SHA256 = "90a49706083c1d1a946e642154c911e8494a76fb51344cc874ba420948fbd93e"


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
