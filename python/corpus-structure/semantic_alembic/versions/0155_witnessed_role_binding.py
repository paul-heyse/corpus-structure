"""Retain witnessed components and frozen source-opportunity frames; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_roles_20261106"
down_revision = "semantic_wce_repair_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_roles_20261106_native.json"
NATIVE_STATE_SHA256 = "d7f6cf82a3eb5831bc7bb0714b80df45d4d584e84b3a89a43d7939ca64537baa"
NATIVE_ADMISSION_FILE = "semantic_wce_roles_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "88f73a43ac6daf35530735caf9a4f26c44767abc2a4f83e1f75c931ee6c75c4b"
NATIVE_UPGRADE_FILE = "semantic_wce_roles_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "39e3f494d72424a148e80279b81c8d3707023e38b8dd6795b72d4542a0b950ab"


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
