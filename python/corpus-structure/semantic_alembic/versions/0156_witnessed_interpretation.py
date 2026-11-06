"""Deploy current witnessed definition, relationship and protected publication contracts."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_meanings_20261106"
down_revision = "semantic_wce_roles_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_witnessed_interpretation_20261106_native.json"
NATIVE_STATE_SHA256 = "dea42958aed26b01512a646344fa61c0893ab7a9786c6d46d1b526e69616b7d9"
NATIVE_ADMISSION_FILE = "semantic_witnessed_interpretation_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "42bb7a763d87cd1fb40ad0df6b08a37f8b1f8406142c75ab224a5d08c9689d27"
NATIVE_UPGRADE_FILE = "semantic_witnessed_interpretation_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "1e3e0f5780644ee2d496fd04f7c53b2b1fe816279008101dcee9000273a5f247"


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
