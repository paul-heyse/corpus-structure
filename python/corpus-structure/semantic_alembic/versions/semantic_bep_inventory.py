"""Apply the frozen native candidate semantic_bep_inventory."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_bep_inventory"
down_revision = "semantic_bep_capacity"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_bep_inventory_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "9ba3727b8af2aebab8f758b854ef46525d115d50329013e5b868a1a16d64705f"
NATIVE_STATE_FILE = "semantic_bep_inventory_native.json"
NATIVE_STATE_SHA256 = "2ab798e01c3d71fa4d8f792aabf0244408184782dad88d54a476c497dacddddb"
NATIVE_ADMISSION_FILE = "semantic_bep_inventory_admission.sql"
NATIVE_ADMISSION_SHA256 = "5e01a3f8f42215c6a38145f340d25f5f167cc536c169d3598ad0b8417cfa3b87"


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
