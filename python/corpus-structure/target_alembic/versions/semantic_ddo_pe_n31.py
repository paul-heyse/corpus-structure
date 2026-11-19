"""Apply the frozen native candidate semantic_ddo_pe_n31."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n31"
down_revision = 'semantic_ddo_pe_n30'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n31_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "0684bef1f727bc92f95ae76d441d6f8db5f57fcc65da86e896f74b2850b22ced"
NATIVE_STATE_FILE = "semantic_ddo_pe_n31_native.json"
NATIVE_STATE_SHA256 = "d17645c15b0fc7ffab195e279f4b68d1a259a5192174ed620f4918edbfecc988"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n31_admission.sql"
NATIVE_ADMISSION_SHA256 = "d8ba3b3babf783c53910d50f40b48272b6ebc9606dc198040fee344b43e751e0"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 2 or state["predecessor"] != down_revision:
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
