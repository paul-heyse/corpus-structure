"""Apply the frozen native candidate semantic_ddo_acquire_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_acquire_v1"
down_revision = "semantic_ddo_admission_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_acquire_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "924f7fd6297fb9b0759afd1666db108576d6fd1231a0865326e1dc5b3b06abd2"
NATIVE_STATE_FILE = "semantic_ddo_acquire_v1_native.json"
NATIVE_STATE_SHA256 = "e6210e108bee214d395b1c31bc3a9eec737a506ce72a1c5ffe0633c73aaa34e0"
NATIVE_ADMISSION_FILE = "semantic_ddo_acquire_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "3c706a52cb4b3ec5a224c3dd3a668c616d3e75d2274b588dfc47306ef14148e4"


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
