"""Apply the frozen native candidate semantic_tc10_11_assessment."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc10_11_assessment"
down_revision = "semantic_tc03_09_literals"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc10_11_assessment_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "3a337f2e929c0ee33b1237865928090a7f965708a385f210f02d6787d95699f0"
NATIVE_STATE_FILE = "semantic_tc10_11_assessment_native.json"
NATIVE_STATE_SHA256 = "981654af107530aa6cd9133a82a3cb0b12b316b710344375a8270314b94b1ff6"
NATIVE_ADMISSION_FILE = "semantic_tc10_11_assessment_admission.sql"
NATIVE_ADMISSION_SHA256 = "23e3c0bf87bfb608ebf184fc3f90cb8634d48f133f852f7319300e6fa13ddb37"


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
