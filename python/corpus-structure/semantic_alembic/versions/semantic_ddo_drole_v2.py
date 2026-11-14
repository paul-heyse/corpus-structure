"""Apply the frozen native candidate semantic_ddo_drole_v2."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_drole_v2"
down_revision = "semantic_ddo_drole_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_drole_v2_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "284d193b33f6c07b9d0b3813454a84e8745e4d72be564e3249345bb17bfc0b8f"
NATIVE_STATE_FILE = "semantic_ddo_drole_v2_native.json"
NATIVE_STATE_SHA256 = "3319934f6e5ca7eaf824a5a2fddab124984e36062360e3b18d9f13926149ee12"
NATIVE_ADMISSION_FILE = "semantic_ddo_drole_v2_admission.sql"
NATIVE_ADMISSION_SHA256 = "4a791ae12d4c520a7505d665f6ccdfb3d49169a2791423200988a8e0937ff7d8"


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
