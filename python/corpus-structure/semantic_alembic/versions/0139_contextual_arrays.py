"""Publish exact local source claims and scoped contextual inputs; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_array_20261105"
down_revision = "semantic_pce_public_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_array_20261105_native.json"
NATIVE_STATE_SHA256 = "e6c7fa26d4a2b8f9447a9b82b5b0635d18dfa805da7b96fc04c65dd9cb75d0f3"
NATIVE_ADMISSION_FILE = "semantic_pce_array_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "330c24495f84a02148a9f002e0871244572532c9a53746bf10e1664eff3148bf"
NATIVE_UPGRADE_FILE = "semantic_pce_array_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "695be377b1b17286636ad88affeb40cad51e08c1bd8660240dda684eee1372a1"


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
