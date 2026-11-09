"""Apply the frozen native candidate semantic_pm2_interpretation."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_interpretation"
down_revision = "semantic_pm2_parser_methods"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_interpretation_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "5e15edcee0b8e2076606102373a934a9456e8e936aaa03a8d739044fe3eb6f29"
NATIVE_STATE_FILE = "semantic_pm2_interpretation_native.json"
NATIVE_STATE_SHA256 = "904948c468cee2177ce7e25dade51bd06d8c184f53998b2d19370854793ff14a"
NATIVE_ADMISSION_FILE = "semantic_pm2_interpretation_admission.sql"
NATIVE_ADMISSION_SHA256 = "2ae0083b937e51c6f7ea92df45f11cf69e116c6296c91ea02387a7c031937860"


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
