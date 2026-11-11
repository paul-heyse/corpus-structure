"""Apply the frozen native candidate semantic_tc10_task_semantics."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc10_task_semantics"
down_revision = "semantic_tc11_view_capacity"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc10_task_semantics_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "13579f87f0678f4b52050fb8d7a576c909bf35f9f1bc70ccca6b3255ea2ce2f6"
NATIVE_STATE_FILE = "semantic_tc10_task_semantics_native.json"
NATIVE_STATE_SHA256 = "89fe12080c69878aceb4edf8ceb668d4a9a0d26a88954bff6bd65c479766bc66"
NATIVE_ADMISSION_FILE = "semantic_tc10_task_semantics_admission.sql"
NATIVE_ADMISSION_SHA256 = "bd96e34eb1e68c9cef8fe04d7027cabb9aa337f02977bb0a5029649fa56cb2ba"


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
