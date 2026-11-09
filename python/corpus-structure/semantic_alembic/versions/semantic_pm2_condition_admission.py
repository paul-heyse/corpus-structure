"""Apply the frozen native candidate semantic_pm2_condition_admission."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_condition_admission"
down_revision = "semantic_pm2_bounded_retrieval"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_condition_admission_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "b01c7e5abcde65773bb79ce445672be1834f852074b0672f636a6a1b5ff26f44"
NATIVE_STATE_FILE = "semantic_pm2_condition_admission_native.json"
NATIVE_STATE_SHA256 = "a06a89559d829d90ed269317676064d4ced0c2730c12cb6cf5d48c1328842311"
NATIVE_ADMISSION_FILE = "semantic_pm2_condition_admission_admission.sql"
NATIVE_ADMISSION_SHA256 = "a13916ac7fe5fdca93d653d7e9ca851356e8421d56b2c5661250f6dcd3310e24"


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
