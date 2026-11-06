"""Expose fitted parameters through an owned operation while protecting reference data."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_params_20261106"
down_revision = "semantic_wce_access_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_params_20261106_native.json"
NATIVE_STATE_SHA256 = "9d9b946f89baca88460e976b58d17cedfaf6dbc5a34ff66bb649096c7a89b099"
NATIVE_ADMISSION_FILE = "semantic_wce_params_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "3135c3ada96d4a3a3349e4b5b20c56b07621322252714fe96f4a5737def26f04"
NATIVE_UPGRADE_FILE = "semantic_wce_params_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "9baa218516d1b2e8b96417cc7b431e29ca6ac81cbd49e0a9bd4ba7d432a829ce"


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
