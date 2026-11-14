"""Apply the frozen native candidate semantic_ddo_found_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_found_v1"
down_revision = "semantic_ddo_origeps_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_found_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "7cf171521e6eaf9fd08700d78b8195fd87e6caa853526362edc8d3d3e236e9c5"
NATIVE_STATE_FILE = "semantic_ddo_found_v1_native.json"
NATIVE_STATE_SHA256 = "ae10ddabdb96142538e65b97ed3c1178598d6db8c5564d37a429f3d92944cfdc"
NATIVE_ADMISSION_FILE = "semantic_ddo_found_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "9009971c719eecf47fe27318ba2232af24adf6c5372daefaeec7e9d9d182d59d"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] not in {1, 2} or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))
    if state["version"] == 2:
        from corpus_structure.semantic.alembic_privileges import admit_privileges
        admit_privileges(op.get_bind(), state["privileges"])


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
