"""Compare frozen structural derivation numbers canonically."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_defnumeric_20261105"
down_revision = "semantic_pce_defvalue_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_defnumeric_20261105_native.json"
NATIVE_STATE_SHA256 = "cc2066a89552f0efb34cc0f0939146fc71c6debe974484b5bfda8b7101b77443"
NATIVE_ADMISSION_FILE = "semantic_pce_defnumeric_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "c17163825e9df61a67841e20e56cb759ff6ead6bb295b610f0a9e0744e216d14"
NATIVE_UPGRADE_FILE = "semantic_pce_defnumeric_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "6760bc2cd8f71ebaec7a46e6b4c718ca9181b55439abdf92ce257a9bf950aa80"


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
