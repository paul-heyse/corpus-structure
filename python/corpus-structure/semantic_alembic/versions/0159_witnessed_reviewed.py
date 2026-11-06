"""Enforce reviewed applicability, ambiguity, original-source selection and dossier semantics."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_reviewed_20261106"
down_revision = "semantic_wce_facts_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_reviewed_20261106_native.json"
NATIVE_STATE_SHA256 = "32db94d809a78bdb94e841bbe4b3ec65cadea69a86602ccd3d57defa5db901a3"
NATIVE_ADMISSION_FILE = "semantic_wce_reviewed_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "7577af125071995c5f74f554e4f7985955b8a01a8b03c4f974dbd89ec1d0b55f"
NATIVE_UPGRADE_FILE = "semantic_wce_reviewed_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "57b6ea180d9c09b1831e94430dd85a3be842c1696ff42ad80e166f71caf20260"


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
