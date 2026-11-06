"""Qualify retained relationship selection aggregation at native applicability completion."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_selection_20261106"
down_revision = "semantic_wce_groups_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_selection_20261106_native.json"
NATIVE_STATE_SHA256 = "9dd3ea6b1c4d07d28ee582e479a27d488abef573f9ba038931917005da6c8b0e"
NATIVE_ADMISSION_FILE = "semantic_wce_selection_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "6adac1bacb4f4db911cd7f59e5aa8dd61ec0e3ff366efee1fb5ee35b0ef10355"
NATIVE_UPGRADE_FILE = "semantic_wce_selection_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e26fcc7bc7a8f44805520e356c9ee0e8c9750752fb81fc46017586b32bce219f"


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
