"""Apply the frozen native candidate semantic_ddo_domain_v9."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_domain_v9"
down_revision = "semantic_ddo_domain_v8"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_domain_v9_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "aa717c2fc80b83c37d3fc67c779262f02344b8b3923201e1c8b58481a8765cd0"
NATIVE_STATE_FILE = "semantic_ddo_domain_v9_native.json"
NATIVE_STATE_SHA256 = "70690a6f6e094369a6b9ff64415be611aeeeb4028ca3d05edb1e1754a7f64fa0"
NATIVE_ADMISSION_FILE = "semantic_ddo_domain_v9_admission.sql"
NATIVE_ADMISSION_SHA256 = "7bc503d2259d8c5ad64f5468bcc071c9fd5106f0002b5453cdfc42d1fbcf689c"


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
