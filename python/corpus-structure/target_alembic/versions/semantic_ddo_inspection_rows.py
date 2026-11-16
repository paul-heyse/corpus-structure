"""Apply the frozen native candidate semantic_ddo_inspection_rows."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_inspection_rows"
down_revision = 'semantic_ddo_current_root'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_inspection_rows_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "69e9956f34d79315f4892ae6a2d703abb9b7f0071ed556725091a4ec2a55feb8"
NATIVE_STATE_FILE = "semantic_ddo_inspection_rows_native.json"
NATIVE_STATE_SHA256 = "f3daf2f3cf592e86053dd6cec0bceb3c0d4f0b2cecc4d0226df5999b0e821241"
NATIVE_ADMISSION_FILE = "semantic_ddo_inspection_rows_admission.sql"
NATIVE_ADMISSION_SHA256 = "5ffa4b3ee4769fbf589551e8934379fbdb261a4ebf99cc849b46e2c931735974"


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
