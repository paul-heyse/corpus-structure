"""Apply the frozen native candidate semantic_ddo_pe_n25."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n25"
down_revision = 'semantic_ddo_pe_n24'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n25_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "afa2f6b51a9e875e66ba6a7ec51a69bccd34552a05f770311328a841b237640e"
NATIVE_STATE_FILE = "semantic_ddo_pe_n25_native.json"
NATIVE_STATE_SHA256 = "4e9483cc4d19820275f13900f0f51eb655d880fab1f0c3e1229ca7fbac4d5b78"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n25_admission.sql"
NATIVE_ADMISSION_SHA256 = "3beb79c88eea6bd60667b520921184b65ebc4dceb094c85f4e333a74ce90e7c6"


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
