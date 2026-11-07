"""Authenticate WCE relation, revision lineage and registered table-policy custody."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_lineage_20261107"
down_revision = "semantic_wce_gaps_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_lineage_20261107_native.json"
NATIVE_STATE_SHA256 = "af03ceb6cba8662dd43027306f3b3c7350d08c2801efb7e3dca36789b9188bab"
NATIVE_ADMISSION_FILE = "semantic_wce_lineage_20261107_admission.sql"
NATIVE_ADMISSION_SHA256 = "6ed819fb475a093fe983efa164ce522632ea1f3da7018e121dc8dfa2cf2411a7"
NATIVE_UPGRADE_FILE = "semantic_wce_lineage_20261107_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "9ec8edc90a4a1f80c80a424e3a2f7da3b0437dc350be269c05b5cc61aa1cbe82"


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
