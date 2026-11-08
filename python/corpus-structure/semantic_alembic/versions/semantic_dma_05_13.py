"""Apply the frozen native candidate semantic_dma_05_13."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_dma_05_13"
down_revision = "semantic_dma_00_04"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_dma_05_13_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "10864a6942cdbf6f93d5cd2e7d23f1654a93a219247e3af94a1e0b09f4b7601a"
NATIVE_STATE_FILE = "semantic_dma_05_13_native.json"
NATIVE_STATE_SHA256 = "d788db1f8737fe22d88d2f90cfdc4377b55cedb3c5dc60107a291a9ef98d7316"
NATIVE_ADMISSION_FILE = "semantic_dma_05_13_admission.sql"
NATIVE_ADMISSION_SHA256 = "90300719d0dadd0367760c7df81208594131eb7b2359f75a3d49e0a3858176b9"


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
