"""Apply the frozen native candidate semantic_tc02_foundation."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc02_foundation"
down_revision = "semantic_dmc_completion_repairs"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc02_foundation_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "2304f9e7110b8844f4a0465afb7a3c63c9f65fd115db5d0ab67086301c66728c"
NATIVE_STATE_FILE = "semantic_tc02_foundation_native.json"
NATIVE_STATE_SHA256 = "2b400caa9524d646591c86c27b10ded96cb8f6080980da8d1cf5e1a39488e8b1"
NATIVE_ADMISSION_FILE = "semantic_tc02_foundation_admission.sql"
NATIVE_ADMISSION_SHA256 = "d64121363a91627e1d2a7165ee595050bdda02abe8e0e7f8e0f93e40092add09"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
