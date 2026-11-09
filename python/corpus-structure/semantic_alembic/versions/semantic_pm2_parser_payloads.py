"""Apply the frozen native candidate semantic_pm2_parser_payloads."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_parser_payloads"
down_revision = "semantic_pm2_def_scope_vars"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_parser_payloads_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "323bfed8f36b13221797227718a185df63a06421b5605ddec9a4efa01b374727"
NATIVE_STATE_FILE = "semantic_pm2_parser_payloads_native.json"
NATIVE_STATE_SHA256 = "ebe59302d141f2feed632986ade49eefd86b7a99c37c463c310563fd00089633"
NATIVE_ADMISSION_FILE = "semantic_pm2_parser_payloads_admission.sql"
NATIVE_ADMISSION_SHA256 = "faeeb38497160f86df01d631cae6594a86b87fc73b4f06f24ad9a81f8ee5ef1a"


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
