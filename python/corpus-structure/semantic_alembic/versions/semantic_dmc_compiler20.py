"""Apply the frozen native candidate semantic_dmc_compiler20."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_dmc_compiler20"
down_revision = "semantic_dmc_inspection"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_dmc_compiler20_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "0376e9083cf679800e9973938ede24608668f5cdf7e457d3fc9c9461aa5c43c0"
NATIVE_STATE_FILE = "semantic_dmc_compiler20_native.json"
NATIVE_STATE_SHA256 = "b7dd518b6c43768222ddb6cc8dda737c7a79b734b1dc679e121573cecfb05f3e"
NATIVE_ADMISSION_FILE = "semantic_dmc_compiler20_admission.sql"
NATIVE_ADMISSION_SHA256 = "b27c2d999d479bb5e61c6e522a67c75839924b68b1ba4204180b12342548f374"


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
