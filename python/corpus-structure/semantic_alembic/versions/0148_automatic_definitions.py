"""Execute source-backed automatic definitions and bounded protected review."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_defauto_20261105"
down_revision = "semantic_pce_structpub_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_defauto_20261105_native.json"
NATIVE_STATE_SHA256 = "6c5d43bf5bf37c2e025d39351b76aed9954b05dd3f46752a912a3b43dec865c3"
NATIVE_ADMISSION_FILE = "semantic_pce_defauto_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "1022a7a1bb0a935e3c8d5c914ba3fd21619ed8b6fec5e15b6e20c27ca4f5667a"
NATIVE_UPGRADE_FILE = "semantic_pce_defauto_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d45fc16130d723eadc47c01d1e4d66bdaef46bb1db93ae9ef5be9417f91d1bda"


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
