"""Apply the frozen native candidate semantic_ddo_selected_proofs."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_selected_proofs"
down_revision = 'semantic_ddo_binding_reuse'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_selected_proofs_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "179dc0c4bbaaac53bbb388746a659a4f5264aefe937779a1031f1a5a4e33c1c7"
NATIVE_STATE_FILE = "semantic_ddo_selected_proofs_native.json"
NATIVE_STATE_SHA256 = "8819642930515bf13af0fa0a6704372d95fd163607fb72084f0c0c7c5b52a8ac"
NATIVE_ADMISSION_FILE = "semantic_ddo_selected_proofs_admission.sql"
NATIVE_ADMISSION_SHA256 = "6a6dd0ae9b983fff544cc14a61adb4a7818f74ed2d65c2817cac4f51b26be656"


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
