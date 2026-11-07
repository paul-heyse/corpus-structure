"""Apply the frozen native candidate semantic_nce_source_roles."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_source_roles"
down_revision = "semantic_cli_run_supervisor"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_source_roles_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "884b95f87eaee814744c2eb0a4cb1e86e606d1b7888bf3fe037c4a97c2ce7de4"
NATIVE_STATE_FILE = "semantic_nce_source_roles_native.json"
NATIVE_STATE_SHA256 = "f772aa25a1748c9e01aa772f0751cff454a72e7a8792c0920684cf40218eb1c7"
NATIVE_ADMISSION_FILE = "semantic_nce_source_roles_admission.sql"
NATIVE_ADMISSION_SHA256 = "6d0372a8920f386095cd358434d7ac4dade2a7b315fd295496016d90a950100d"


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
