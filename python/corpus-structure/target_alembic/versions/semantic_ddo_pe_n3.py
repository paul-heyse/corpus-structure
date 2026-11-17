"""Apply the frozen native candidate semantic_ddo_pe_n3."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n3"
down_revision = 'semantic_ddo_pe_n2'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n3_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "4ec7bef8744fc80d040db1ae87944a5780976b89ce1af8981b8a9d3e6a7f72e3"
NATIVE_STATE_FILE = "semantic_ddo_pe_n3_native.json"
NATIVE_STATE_SHA256 = "885b85ac2cb0096c571eba8260caa3b0409ca859bd8254a1521b7b866a151800"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n3_admission.sql"
NATIVE_ADMISSION_SHA256 = "533eb36668771d9a67a85f7985459b3549064c7f43a41f4b348998e820448737"


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
