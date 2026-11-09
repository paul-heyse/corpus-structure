"""Apply the frozen native candidate semantic_pm2_def_scope_vars."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_def_scope_vars"
down_revision = "semantic_pm2_definition_scope"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_def_scope_vars_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "0e9250f854ac10a44f4d2c1aa46441eb7caff29dc697da104e3bac458f1f4cc5"
NATIVE_STATE_FILE = "semantic_pm2_def_scope_vars_native.json"
NATIVE_STATE_SHA256 = "a9eea408807eb42afa0f8d57b09394d8956b87dd399be29702a4f97be3543e1e"
NATIVE_ADMISSION_FILE = "semantic_pm2_def_scope_vars_admission.sql"
NATIVE_ADMISSION_SHA256 = "ba1931269683e494a773ae40ea690abb17ca93dc8e5a0dfad5d7a3f6f7e33b33"


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
