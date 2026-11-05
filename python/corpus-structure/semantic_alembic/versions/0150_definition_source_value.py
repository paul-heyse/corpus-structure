"""Validate automatic definition typed source provenance."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_defvalue_20261105"
down_revision = "semantic_pce_defbind_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_defvalue_20261105_native.json"
NATIVE_STATE_SHA256 = "de3325625c21b576586330f67daebde1692f1058a83d998f6241be558159f572"
NATIVE_ADMISSION_FILE = "semantic_pce_defvalue_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "ac92a5257e356e81650247e3db714b4b6c6d2bb5285154d57e8a2650037ee0d4"
NATIVE_UPGRADE_FILE = "semantic_pce_defvalue_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "64b8b0277b6db8821cf66d040595bc787e8c1cee29b11e426077a15bf9a6ae8e"


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
