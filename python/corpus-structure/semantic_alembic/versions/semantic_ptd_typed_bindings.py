"""Apply the frozen native candidate semantic_ptd_typed_bindings."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ptd_typed_bindings"
down_revision = "semantic_pm2_named_pieces"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ptd_typed_bindings_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "350473577555eccd0ffd097a09ab1649b18f5dabc6afc72d3577c41713aa9080"
NATIVE_STATE_FILE = "semantic_ptd_typed_bindings_native.json"
NATIVE_STATE_SHA256 = "abf36863f81c7d61f2b34d1c1edd5146860fce004eead0e4d5ad84e512b5d8ce"
NATIVE_ADMISSION_FILE = "semantic_ptd_typed_bindings_admission.sql"
NATIVE_ADMISSION_SHA256 = "8db07efb8d0cef7803a461e05c4c7aa18dd2b06e473652731e29548d92433fd1"


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
