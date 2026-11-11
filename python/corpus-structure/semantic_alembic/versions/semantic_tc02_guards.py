"""Apply the frozen native candidate semantic_tc02_guards."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc02_guards"
down_revision = "semantic_tc02_products"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc02_guards_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "3120c1106dd5f7d812d500de24f60717ca5f91cdb4f9cf8fb195c315452ec640"
NATIVE_STATE_FILE = "semantic_tc02_guards_native.json"
NATIVE_STATE_SHA256 = "a131e2db43b4f26ab7316460628316d3653ff88ac8941f643d6ed2f134198111"
NATIVE_ADMISSION_FILE = "semantic_tc02_guards_admission.sql"
NATIVE_ADMISSION_SHA256 = "1324e225a37e6a601275a9255805cd215cc1f84e370c1c8d3998e14a13f61085"


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
