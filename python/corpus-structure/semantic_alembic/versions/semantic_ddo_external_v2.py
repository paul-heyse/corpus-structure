"""Apply the frozen native candidate semantic_ddo_external_v2."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_external_v2"
down_revision = "semantic_ddo_external_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_external_v2_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "66aae96555e0e9f51c4805c6fb94cd099df9dfa31a4408be27f3970fcfe432e1"
NATIVE_STATE_FILE = "semantic_ddo_external_v2_native.json"
NATIVE_STATE_SHA256 = "0f4ad39a04a52aa044b7fc7eba169f0a54d29b9dc6c5ee0eed38ec79e64c9948"
NATIVE_ADMISSION_FILE = "semantic_ddo_external_v2_admission.sql"
NATIVE_ADMISSION_SHA256 = "4f5c1a706d10ed5046784b468f0577cfeca2ba61e71af7ae33e779770a82d824"


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
