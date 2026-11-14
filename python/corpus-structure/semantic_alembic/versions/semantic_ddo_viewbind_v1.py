"""Apply the frozen native candidate semantic_ddo_viewbind_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_viewbind_v1"
down_revision = "semantic_ddo_sources_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_viewbind_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "f6225cce0cc88e25da249041435ffa98541152605775d4822ede5a9f0b3c1368"
NATIVE_STATE_FILE = "semantic_ddo_viewbind_v1_native.json"
NATIVE_STATE_SHA256 = "6f511512afdd5dd4d820f7f1e34294d509dfd7b19e0ce392681b2049ba1cdf06"
NATIVE_ADMISSION_FILE = "semantic_ddo_viewbind_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "d80ec9be3e1e4a183515637454e07646419f73a8bf9fe52f21449b64ce6a8341"


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
