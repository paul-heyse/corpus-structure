"""Publish exact local source claims and scoped contextual inputs; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_public_20261105"
down_revision = "semantic_pce_custody_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_public_20261105_native.json"
NATIVE_STATE_SHA256 = "e2baf715084523de61166bada0e8146b216e9570d176f97ca51044d764c0b690"
NATIVE_ADMISSION_FILE = "semantic_pce_public_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "72b213259503b80128e580b12b8bea81601fc62e1f5145e802810947319def89"
NATIVE_UPGRADE_FILE = "semantic_pce_public_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "52f4c266995baf239a84556e5bb3407b55bc7d7329dae9817813fe89d806e66f"


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
