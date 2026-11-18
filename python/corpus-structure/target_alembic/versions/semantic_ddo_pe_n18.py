"""Apply the frozen native candidate semantic_ddo_pe_n18."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n18"
down_revision = 'semantic_ddo_pe_n17'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n18_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "351de3da0370de9db85ab53cb9d86a0be7a1abbaa29ecfcc6b2c2e0d135cd378"
NATIVE_STATE_FILE = "semantic_ddo_pe_n18_native.json"
NATIVE_STATE_SHA256 = "87e0020129caa90cc727a82168a1e9291c09d1aee2142b4da202058c31b0a875"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n18_admission.sql"
NATIVE_ADMISSION_SHA256 = "8c74eb49ebe89bc0d5f1c8bfc2fe58c87970178fbf003b96c93d9325bdc2a3c9"


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
