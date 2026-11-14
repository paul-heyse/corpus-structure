"""Apply the frozen native candidate semantic_ddo_inputs_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_inputs_v1"
down_revision = "semantic_ddo_context_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_inputs_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "c0449633e21dd4ab57c5ef58d0fd779004ad243154f8cc133198649fe5a487bc"
NATIVE_STATE_FILE = "semantic_ddo_inputs_v1_native.json"
NATIVE_STATE_SHA256 = "3835bba8abb7d3d5bb5b6c19d98a4b0a9fab7c3422f260d1675b70ffa837d34d"
NATIVE_ADMISSION_FILE = "semantic_ddo_inputs_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "589cf408f1853ff52f27b5090ab7f15d01353b3d9e53331596643a42bf7703f9"


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
