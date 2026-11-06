"""Retain witnessed components and frozen source-opportunity frames; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_components_20261106"
down_revision = "semantic_test_rowtype_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_components_20261106_native.json"
NATIVE_STATE_SHA256 = "09581df5d2ff855565d876862bb0baa742d79755d12186b0f2b8d18c7f8335f1"
NATIVE_ADMISSION_FILE = "semantic_wce_components_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "318fe838e0b85926ab6970dd6402c313d92c437a9e03d498881122a626345b10"
NATIVE_UPGRADE_FILE = "semantic_wce_components_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "eaad023d23b9cdfb76310dd4d042af085c082b1af823362c13828c8cf56fcd93"


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
