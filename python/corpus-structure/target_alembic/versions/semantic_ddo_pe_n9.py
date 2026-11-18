"""Apply the frozen native candidate semantic_ddo_pe_n9."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n9"
down_revision = 'semantic_ddo_pe_n8'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n9_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "8f9bd6c9894b4335f86cdc705cce759c1ba39898a6c481d074d056c85152f901"
NATIVE_STATE_FILE = "semantic_ddo_pe_n9_native.json"
NATIVE_STATE_SHA256 = "411294a64632169358c819b6cdac201e28fea826b91e85b23bc814103b6d54d1"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n9_admission.sql"
NATIVE_ADMISSION_SHA256 = "317ccc36a23a793a8706390b51be95f0472fb6ec8eab0178d76d8186bf264ffd"


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
