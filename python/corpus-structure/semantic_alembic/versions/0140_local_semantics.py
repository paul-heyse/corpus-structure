"""Publish independently judged local semantics through common consolidation; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_semantics_20261105"
down_revision = "semantic_pce_array_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_semantics_20261105_native.json"
NATIVE_STATE_SHA256 = "0c222e873aa1d1458288a8bbc858bf6dec83c76478a2b465365f8b8e8455512b"
NATIVE_ADMISSION_FILE = "semantic_pce_semantics_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "ef0eba22ea68418515781db23cb711d777420f188336a994183db83c874c9f93"
NATIVE_UPGRADE_FILE = "semantic_pce_semantics_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "9ae473fe2cbbbdbf8ccd77ac2d8f1d136aadd9465b962d546622890df86a1531"


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
