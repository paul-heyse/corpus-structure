"""Enforce exact semantic target groups, source preparation privileges and source-resolved evidence parity."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_groups_20261106"
down_revision = "semantic_wce_reviewed_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_groups_20261106_native.json"
NATIVE_STATE_SHA256 = "8a495dd4cc1b410f3f1ae07a32b10d5b63e8439ea8094db1aabe6e18d231fea1"
NATIVE_ADMISSION_FILE = "semantic_wce_groups_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "c5316cacfc63acab67104f6ff873408a0a85f42183fc24c85669a88ca074989f"
NATIVE_UPGRADE_FILE = "semantic_wce_groups_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d3e941feba0318d4e2483d617d3bc31ecde10940c48c86d0f33048e42b35df41"


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
