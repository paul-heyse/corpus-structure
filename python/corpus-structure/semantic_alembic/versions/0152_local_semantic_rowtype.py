"""Keep local semantic guard rows stable across temporary staging lifetimes."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_test_rowtype_20261105"
down_revision = "semantic_pce_defnumeric_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_test_rowtype_20261105_native.json"
NATIVE_STATE_SHA256 = "d3c41cdd666d7a4cb596c000ac1dadf7f4f9228c68f017ad2c34b18d0cf1d6a0"
NATIVE_ADMISSION_FILE = "semantic_test_rowtype_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "e59205baa3299bde97605dc1b501a10404014e0ced28fd704e805b2ae90e6345"
NATIVE_UPGRADE_FILE = "semantic_test_rowtype_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "c008175eb501a1036aeb48e4cb70c9b5e767d5637ffaa3fede75d19b33d960f5"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen local publication artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible local publication predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive local publication downgrade refused")
