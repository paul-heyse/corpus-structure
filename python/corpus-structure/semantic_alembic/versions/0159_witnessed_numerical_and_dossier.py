"""Preserve dossier states and enforce complete numerical result invariants."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_complete_20261106"
down_revision = "semantic_wce_composed_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_complete_20261106_native.json"
NATIVE_STATE_SHA256 = "f40591fb13c8c078c56073a7c6343a828d2af70e72b18c9a7dd91523ca883beb"
NATIVE_ADMISSION_FILE = "semantic_wce_complete_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "8c807aeb98b1b780470580a6cba1a1d09fe6b4f2b125b7c9fedf2cb394f9ce26"
NATIVE_UPGRADE_FILE = "semantic_wce_complete_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d470ac7bc8b6082c8b53c9944b92f8aa1cab38e8cf86eb923d64e2baf4291aca"


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
