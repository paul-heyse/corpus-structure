"""Apply the frozen native candidate semantic_tc03_09_dispatch."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc03_09_dispatch"
down_revision = "semantic_tc03_09_finalize"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc03_09_dispatch_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "18fe7744a2017439d973a43de2b205bd26e20975ccdabac2d430d80c958919b4"
NATIVE_STATE_FILE = "semantic_tc03_09_dispatch_native.json"
NATIVE_STATE_SHA256 = "496ad95de102630d6be680f6ee84cce09a88c16b1efab679eaaf5e1339ff39e5"
NATIVE_ADMISSION_FILE = "semantic_tc03_09_dispatch_admission.sql"
NATIVE_ADMISSION_SHA256 = "9c52526ac9836a14abc674f563ae2a04deb402d4d4c8b86a28483b0a718d5d51"


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
