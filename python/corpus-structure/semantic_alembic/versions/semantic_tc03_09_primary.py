"""Apply the frozen native candidate semantic_tc03_09_primary."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc03_09_primary"
down_revision = "semantic_tc02_reachability"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc03_09_primary_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "79e3dda7e662efac3dc5e6dc2108297824a9ac7331e03d06d88bdf8c81da145f"
NATIVE_STATE_FILE = "semantic_tc03_09_primary_native.json"
NATIVE_STATE_SHA256 = "408dd321d23d1622403a21d4e259689edd7bca22fd1115fb1330a9102c0dfe00"
NATIVE_ADMISSION_FILE = "semantic_tc03_09_primary_admission.sql"
NATIVE_ADMISSION_SHA256 = "8ded6e8604945a3ab4c35a339dc989999ca451a8fb27e03d1cfb352aac2f9c14"


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
