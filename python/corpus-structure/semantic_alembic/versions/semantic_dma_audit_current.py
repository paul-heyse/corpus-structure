"""Apply the frozen native candidate semantic_dma_audit_current."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_dma_audit_current"
down_revision = "semantic_dma_05_13_final"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_dma_audit_current_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d785df854644f8253407105ee549c53595de9eebfd6795db40aee29facdc6b1b"
NATIVE_STATE_FILE = "semantic_dma_audit_current_native.json"
NATIVE_STATE_SHA256 = "7f556293c2719b2a801e0607d9e161382ad1e5313e37410c322dbad10c2d3129"
NATIVE_ADMISSION_FILE = "semantic_dma_audit_current_admission.sql"
NATIVE_ADMISSION_SHA256 = "1444eb068ffbdb960ee7700d8973148c5974a4241ceabd2d60f4f2afa39cfc34"


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
