"""Apply the frozen native candidate semantic_pm2_parser_methods."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_parser_methods"
down_revision = "semantic_dma_audit_current"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_parser_methods_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "8a6b1bac9c18c5f0e0be506d8302c27952179515a74b090062ed8376a74c3ae2"
NATIVE_STATE_FILE = "semantic_pm2_parser_methods_native.json"
NATIVE_STATE_SHA256 = "d9a99a29ca7c1216ab149724a718cd664d9d6ee1883a867bbd41128db3832342"
NATIVE_ADMISSION_FILE = "semantic_pm2_parser_methods_admission.sql"
NATIVE_ADMISSION_SHA256 = "6ea1a31ea2a12e67965f484b5c093da2aa36f5a1dba77ab187b4b72fa5fabab7"


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
