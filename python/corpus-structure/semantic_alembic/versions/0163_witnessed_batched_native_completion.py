"""Batch retained dossier custody and decode canonical artifact parameters."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_batch_20261106"
down_revision = "semantic_wce_acl_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_batch_20261106_native.json"
NATIVE_STATE_SHA256 = "623ac6973adabb558be9ab64e4fcf42564c7331d9fa6754b22f0cc038ec681e4"
NATIVE_ADMISSION_FILE = "semantic_wce_batch_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "fe6d71ad9502dad6806ec60b2d38d597eba948411fcf4a1a2cd66ce0c637a755"
NATIVE_UPGRADE_FILE = "semantic_wce_batch_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "965059f7e67ebaa6de01bc8a91adfeec84e4695a22ed7c127f3ef861cb9582f4"


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
