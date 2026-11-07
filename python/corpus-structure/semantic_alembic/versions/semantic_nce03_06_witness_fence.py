"""Apply the frozen native candidate semantic_nce03_06_witness_fence."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce03_06_witness_fence"
down_revision = "semantic_nce03_06_model_fence"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce03_06_witness_fence_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "a3ee16c8e586dee42c24c149ee4d8eb12ad1e6acea09c4cd8712f82dc283152c"
NATIVE_STATE_FILE = "semantic_nce03_06_witness_fence_native.json"
NATIVE_STATE_SHA256 = "f29e67193dd98fbaab8e03120918104cf7844b938f4515c40fb3756329398a43"
NATIVE_ADMISSION_FILE = "semantic_nce03_06_witness_fence_admission.sql"
NATIVE_ADMISSION_SHA256 = "b10b6fd9b2068f98759ceb985dcd24bbc2847dbd93d42e7a827f9da823fb6b7d"


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
