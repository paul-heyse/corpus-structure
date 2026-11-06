"""Deploy source-resolved knowledge statements independent of derivation identifiers."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_facts_20261106"
down_revision = "semantic_wce_policy_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_facts_20261106_native.json"
NATIVE_STATE_SHA256 = "77ebbf2a0a51b0a247aafb7abc88e857d4ba431ed638da1381d3ed223631ae8f"
NATIVE_ADMISSION_FILE = "semantic_wce_facts_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "236841b88be78c9515620ff8754374bb1ead88d002458e994639e3ece2ab1d3a"
NATIVE_UPGRADE_FILE = "semantic_wce_facts_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "c632f96fe79250097376333d93196183688432f22c816e7404dcd4c0ae45553f"


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
