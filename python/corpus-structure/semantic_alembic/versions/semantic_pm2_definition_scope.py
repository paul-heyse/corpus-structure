"""Apply the frozen native candidate semantic_pm2_definition_scope."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_definition_scope"
down_revision = "semantic_pm2_contextual_queries"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_definition_scope_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "fdbd546705d5941ce87bd68fd2d25a425891166dfca9467914e74899b7250041"
NATIVE_STATE_FILE = "semantic_pm2_definition_scope_native.json"
NATIVE_STATE_SHA256 = "3bea9208a9fe49535e3e02ae278262dec66c581b7f5a6e6801463c2c9a462887"
NATIVE_ADMISSION_FILE = "semantic_pm2_definition_scope_admission.sql"
NATIVE_ADMISSION_SHA256 = "e9445a4ffe4b621922874cdf0cfb2db918e0a95bc270ab1df4e20a81186a36d6"


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
