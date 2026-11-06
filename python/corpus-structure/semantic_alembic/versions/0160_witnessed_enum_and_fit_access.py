"""Align dossier interpretation enums and ordinary parameter-only fit access."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_access_20261106"
down_revision = "semantic_wce_complete_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_access_20261106_native.json"
NATIVE_STATE_SHA256 = "fcbc6ec82d1a7a38bec7b0210199e060ca05746c22f37c30dc1eacda427e9d12"
NATIVE_ADMISSION_FILE = "semantic_wce_access_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "788a3bd6688300b0dfc8438fcf5f06d159ddbb80dee33aac1d454d1a78edc051"
NATIVE_UPGRADE_FILE = "semantic_wce_access_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "7d880a25fab13cdce64d1176542f4b363ed14d12213d58b79877c2068e1ca7bf"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen WCE artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible WCE predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive WCE downgrade refused")
