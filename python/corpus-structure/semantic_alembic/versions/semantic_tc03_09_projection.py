"""Apply the frozen native candidate semantic_tc03_09_projection."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc03_09_projection"
down_revision = "semantic_tc03_09_dispatch"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc03_09_projection_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "1405c907ad407305fdca2de7d15b7a2ac3fdff5e39122e713b359660d044c8fc"
NATIVE_STATE_FILE = "semantic_tc03_09_projection_native.json"
NATIVE_STATE_SHA256 = "3b5a936d0e7a2386e1ad4bc4d64dc633e69dfdd824192c84be22ecb440b4827f"
NATIVE_ADMISSION_FILE = "semantic_tc03_09_projection_admission.sql"
NATIVE_ADMISSION_SHA256 = "bb719c65113b9e43f114d06dbcddb3b85e9d2e7af3507644df81922bbe62180e"


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
