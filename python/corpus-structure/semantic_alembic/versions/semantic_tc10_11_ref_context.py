"""Apply the frozen native candidate semantic_tc10_11_ref_context."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc10_11_ref_context"
down_revision = "semantic_tc10_11_assessment"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc10_11_ref_context_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "232b6ad2cffbedf66ba95c45d9b94a402ea9e9690feada3e24b177c6db3bb986"
NATIVE_STATE_FILE = "semantic_tc10_11_ref_context_native.json"
NATIVE_STATE_SHA256 = "35ba5ef6d7c859a5f3a6c1700a00b7de9062a9c7e286fd4286623ee60ab26ece"
NATIVE_ADMISSION_FILE = "semantic_tc10_11_ref_context_admission.sql"
NATIVE_ADMISSION_SHA256 = "668e9c84b5a5bce2e396a8c29b7b31a87f084bd3d01a39fe0cd511550e3dd0c4"


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
