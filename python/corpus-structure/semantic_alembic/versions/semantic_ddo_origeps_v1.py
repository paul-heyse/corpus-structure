"""Apply the frozen native candidate semantic_ddo_origeps_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_origeps_v1"
down_revision = "semantic_ddo_rolesup_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_origeps_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "b9395175351492cd9b16d857b1c0e3aa3b3c9da3b37132724d3a66ca15a47d33"
NATIVE_STATE_FILE = "semantic_ddo_origeps_v1_native.json"
NATIVE_STATE_SHA256 = "2238cb0979d600cadfd41102b03f3027913eb50fe7cb0d730c95f15ea05b9294"
NATIVE_ADMISSION_FILE = "semantic_ddo_origeps_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "3924f9446cdbe9dda47356cca953c4b88d4677509659f6fe1466492e8baac2b8"


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
