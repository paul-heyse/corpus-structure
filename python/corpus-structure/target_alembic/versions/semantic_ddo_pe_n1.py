"""Apply the frozen native candidate semantic_ddo_pe_n1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n1"
down_revision = 'semantic_ddo_policy_json'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "eba481b23809e190e60311a396b933d25e579307d10b79bdc719f204bd4e4c42"
NATIVE_STATE_FILE = "semantic_ddo_pe_n1_native.json"
NATIVE_STATE_SHA256 = "01acdfabb7c54eed52695b4fc6f79e7e0ff210a0b2bbc2bbf30501c0daee9c81"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n1_admission.sql"
NATIVE_ADMISSION_SHA256 = "f66533741e8943a28b3c0e3f976d93edec3e624108a161a50483b4659be57e19"


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
