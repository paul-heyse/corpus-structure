"""Separate raw model definition proposals from retained-component projections."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_baseline_20261106"
down_revision = "semantic_wce_target_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_baseline_20261106_native.json"
NATIVE_STATE_SHA256 = "c7367bb8e48b7c595aad56624cda80b43ba5fabbc2750e7a7a96c32ab756c7b2"
NATIVE_ADMISSION_FILE = "semantic_wce_baseline_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "cb1c51fbc2c536b9d7c995306970428e98e846f1e63cf38346edaf9da2f59869"
NATIVE_UPGRADE_FILE = "semantic_wce_baseline_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "5a26edb710f5ba341cc0d5724e4a8df9616fce41709f1e37fa8ac10c840bd0b1"


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
