"""Apply the frozen native candidate semantic_pm2_bounded_retrieval."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_bounded_retrieval"
down_revision = "semantic_pm2_definition_chain"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_bounded_retrieval_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "c45807bcb8ea6771073fa572406ce042dc17dac9006084c5191ea5ae5b688ca9"
NATIVE_STATE_FILE = "semantic_pm2_bounded_retrieval_native.json"
NATIVE_STATE_SHA256 = "52b78006f2e8a98a2f74c08303327bf971c88c26895df6934a93d5a958acd355"
NATIVE_ADMISSION_FILE = "semantic_pm2_bounded_retrieval_admission.sql"
NATIVE_ADMISSION_SHA256 = "54862dfa4cad06a001f3b75ae8a848fe9de54afb0f6c379be2ccf8208270968b"


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
