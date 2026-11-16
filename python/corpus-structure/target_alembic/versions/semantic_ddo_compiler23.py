"""Apply the frozen native candidate semantic_ddo_compiler23."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_compiler23"
down_revision = 'semantic_ddo_inspection_rows'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_compiler23_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "383b000c8f4de7dd3d0acad2f7c37f2b7084ad61f0f0c2373939eb85890d36e4"
NATIVE_STATE_FILE = "semantic_ddo_compiler23_native.json"
NATIVE_STATE_SHA256 = "b5a4bb0470e23b4b4d9731736ee751b908ebe17c91aad8d8c621fc1df53e19d1"
NATIVE_ADMISSION_FILE = "semantic_ddo_compiler23_admission.sql"
NATIVE_ADMISSION_SHA256 = "49022809a2b7041e07cb7271388ad1ba9435e4ca3d89fafa4f30df656ec4caf8"


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
