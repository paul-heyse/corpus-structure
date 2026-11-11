"""Apply the frozen native candidate semantic_tc02_products."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc02_products"
down_revision = "semantic_tc02_foundation"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc02_products_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "77dff14b3bcda7c14ccf62e3e9c0d9d396f10988783e330fbf1fe90a8d2ba163"
NATIVE_STATE_FILE = "semantic_tc02_products_native.json"
NATIVE_STATE_SHA256 = "f9bb85ce1d31d75a492482e95366d5e605c13430ee6a783043522908881d1b2a"
NATIVE_ADMISSION_FILE = "semantic_tc02_products_admission.sql"
NATIVE_ADMISSION_SHA256 = "96a759f01c47553f0626981e9e9f31c6d3dfb8258c60c55d1bb1868f7e852106"


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
