"""Apply the frozen native candidate semantic_pm2_contextual_queries."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_contextual_queries"
down_revision = "semantic_pm2_interpretation"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_contextual_queries_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "4fe360025c8a00b9b6f040f3ac905a2ed877dad9ee1eefbde3759130850ba883"
NATIVE_STATE_FILE = "semantic_pm2_contextual_queries_native.json"
NATIVE_STATE_SHA256 = "a00f5db85d6e493df5ceac20de75a0c735606d1b9ee250e2652359227834b2e6"
NATIVE_ADMISSION_FILE = "semantic_pm2_contextual_queries_admission.sql"
NATIVE_ADMISSION_SHA256 = "480d6ca91eabf78d395aa9030bd608a72e7075f560561ce8d8fc006eb98f94e7"


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
