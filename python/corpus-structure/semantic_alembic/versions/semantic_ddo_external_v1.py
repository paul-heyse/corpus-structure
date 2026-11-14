"""Apply the frozen native candidate semantic_ddo_external_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_external_v1"
down_revision = "semantic_ddo_facts_v2"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_external_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "83ce1bb019abf8b3c510f65e565c83b86bb1e3a4d2280fbfdf903d1334ed9041"
NATIVE_STATE_FILE = "semantic_ddo_external_v1_native.json"
NATIVE_STATE_SHA256 = "c3c05fac8bd65721111b4ca4824339bcce31e576b39907fa1637274e99e39b3c"
NATIVE_ADMISSION_FILE = "semantic_ddo_external_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "295609c10e8a400d0de6f883c4898a0746b9b7c04f0fd114b7087c55405d4f61"


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
