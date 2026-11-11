"""Apply the frozen native candidate semantic_tc02_cross_release."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc02_cross_release"
down_revision = "semantic_tc02_guards"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc02_cross_release_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "7e50843a3fb5536d3025c65d2d2663ae388cc3cf40195a2d32e3dc502f9897b1"
NATIVE_STATE_FILE = "semantic_tc02_cross_release_native.json"
NATIVE_STATE_SHA256 = "34e69a7f1b19f61024e4c30d0e0e34625dec0d6a7d7691a0d9b6e653ea6acb19"
NATIVE_ADMISSION_FILE = "semantic_tc02_cross_release_admission.sql"
NATIVE_ADMISSION_SHA256 = "36d610f547a420c8f08fd323dd4b8a7037598254198f9fe54027cfd6274d129d"


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
