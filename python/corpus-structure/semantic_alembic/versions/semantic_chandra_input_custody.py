"""Apply the frozen native candidate semantic_chandra_input_custody."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_chandra_input_custody"
down_revision = "semantic_chandra_stage_schema"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_chandra_input_custody_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "0b1ff2daddd5ea740405c4ecce3b8ccb6ba1a03904736af6a2f6646ad4996aa1"
NATIVE_STATE_FILE = "semantic_chandra_input_custody_native.json"
NATIVE_STATE_SHA256 = "f7c5a3b7a05ad8bb0016debe08aba286ff33f21ca2e2283c5cd63cab9fc6991f"
NATIVE_ADMISSION_FILE = "semantic_chandra_input_custody_admission.sql"
NATIVE_ADMISSION_SHA256 = "b8301028226456a0b8ff49b601c15039e48800d9b3386769d7e98345f9d78ee6"


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
