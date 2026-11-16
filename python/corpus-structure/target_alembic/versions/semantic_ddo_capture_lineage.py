"""Apply the frozen native candidate semantic_ddo_capture_lineage."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_capture_lineage"
down_revision = 'semantic_ddo_consumer_fixes'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_capture_lineage_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "fab8bc374e6721c9f243dafc8ed3ec9f5b99cfdd82fc118f3088b7f2eb8be71c"
NATIVE_STATE_FILE = "semantic_ddo_capture_lineage_native.json"
NATIVE_STATE_SHA256 = "5542c011513afa8ba190ee9858690f7d6a6b20a3b0e8ff787ba03f5f620d625a"
NATIVE_ADMISSION_FILE = "semantic_ddo_capture_lineage_admission.sql"
NATIVE_ADMISSION_SHA256 = "0082bba29a1c983938ec70967c426255364f8c4b857f5c5553a788bb0db841ac"


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
