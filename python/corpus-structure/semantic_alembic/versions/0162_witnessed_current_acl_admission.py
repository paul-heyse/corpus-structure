"""Derive current execution-role admission from the complete normalized ACL."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_acl_20261106"
down_revision = "semantic_wce_params_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_acl_20261106_native.json"
NATIVE_STATE_SHA256 = "9f47a44db313dbe893e0fbee3debd5652cbc02cf8f3407d0b3b76c6aead43c2a"
NATIVE_ADMISSION_FILE = "semantic_wce_acl_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "8978e0c7883886daf220c3e7f9186f0d7c6c8d2a4791aac697528c1e8e93a66f"
NATIVE_UPGRADE_FILE = "semantic_wce_acl_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "2db8b4652bd127e85fa24b2ee9decf49bed7040f6879764919f1667a30ddf4d3"


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
