"""Apply the frozen native candidate semantic_ddo_current_root."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_current_root"
down_revision = None
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_current_root_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "4fe417a7f4f76bca6efef5bdb92567dd082798cfec6813482fc1de6e03ad09c5"
NATIVE_STATE_FILE = "semantic_ddo_current_root_native.json"
NATIVE_STATE_SHA256 = "bb698a6f53cb42eaacaf9bf31190e110d65b6cd056459335df442d342d85b42e"
NATIVE_ADMISSION_FILE = "semantic_ddo_current_root_admission.sql"
NATIVE_ADMISSION_SHA256 = "e861f313ac534272c42a3eb32d9198079cbe9b72d97dcc43e80e6bcee65eedc4"


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
