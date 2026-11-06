"""Qualify the independent premise predicate at native applicability completion."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_premise_20261106"
down_revision = "semantic_wce_selection_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_premise_20261106_native.json"
NATIVE_STATE_SHA256 = "6cc5493d8d0e608a087a5198a6840797ffde44a25dc7ba6df761d766d35f496d"
NATIVE_ADMISSION_FILE = "semantic_wce_premise_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "f347266d4753c8060f1d98f6d7c668e705ec1be900ce30d0ae19465589642831"
NATIVE_UPGRADE_FILE = "semantic_wce_premise_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "ae43f5e4b7322e78bd39e32409647ba02b78201b37d25d71b62074d32cd88272"


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
