"""Apply the frozen native candidate semantic_nce_audit_named_piece."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_audit_named_piece"
down_revision = "semantic_nce_audit_blocks"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_audit_named_piece_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "5b10e02a6b0df50e6cddb2d139d0bcda24d8a4f2b690672e2998358df8c0c1e2"
NATIVE_STATE_FILE = "semantic_nce_audit_named_piece_native.json"
NATIVE_STATE_SHA256 = "39cad66167422b75c6026ca7c6dab5b8163de434b6df86d225505ad1bdcddd72"
NATIVE_ADMISSION_FILE = "semantic_nce_audit_named_piece_admission.sql"
NATIVE_ADMISSION_SHA256 = "2c76574992f767bd5ce3a4e2a8c71a8642cfb19036e29481ac592c4c64ee7a72"


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
