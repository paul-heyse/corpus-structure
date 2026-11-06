"""Install the current witnessed component, relationship and applicability design."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_target_20261106"
down_revision = "semantic_wce_roles_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_target_20261106_native.json"
NATIVE_STATE_SHA256 = "f288880ae03211bddeb1e81a9c3392fcab25b6d55a279d8854794f9822121949"
NATIVE_ADMISSION_FILE = "semantic_wce_target_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "cad18457c2a669b370c4798ccd2cb41b3d085f07baf3dbf3d6279c372aec6339"
NATIVE_UPGRADE_FILE = "semantic_wce_target_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "4d90b9fdad01ad6c8a10085c2d5048ad55867349ff1faf4ecabcd1b712763d5e"


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
