"""Apply the frozen native candidate semantic_chandra_inspection."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_chandra_inspection"
down_revision = "semantic_nce_gs518_discourse"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_chandra_inspection_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "5fb5487702bff7e26efbebb9a3eb030fe2cb1172b754662abb7906380d08c2ea"
NATIVE_STATE_FILE = "semantic_chandra_inspection_native.json"
NATIVE_STATE_SHA256 = "dc07603041f0ec0a837779b145ed30fa064c4d096ebde200680f9e0752265519"
NATIVE_ADMISSION_FILE = "semantic_chandra_inspection_admission.sql"
NATIVE_ADMISSION_SHA256 = "4e18bc81f4052ecebf242a11a2c235c6ed38a6b197f2e23ea470eabb5c25494f"


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
