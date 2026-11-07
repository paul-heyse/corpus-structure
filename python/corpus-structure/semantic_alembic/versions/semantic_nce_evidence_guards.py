"""Apply the frozen native candidate semantic_nce_evidence_guards."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_evidence_guards"
down_revision = "semantic_nce_source_roles"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_evidence_guards_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "574dc72007966005b614606755ef2a0148efa357b3a7fc753326a098bd2017c1"
NATIVE_STATE_FILE = "semantic_nce_evidence_guards_native.json"
NATIVE_STATE_SHA256 = "7fdd295eb94617c3d55472c47c05b09cbcc2ff8b84b83bd0e680dd0ebaa7281c"
NATIVE_ADMISSION_FILE = "semantic_nce_evidence_guards_admission.sql"
NATIVE_ADMISSION_SHA256 = "f2b01f941d863a45f6d7d2ee4c6e6157f7855ec5618a0d85ba2f8563189f1395"


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
