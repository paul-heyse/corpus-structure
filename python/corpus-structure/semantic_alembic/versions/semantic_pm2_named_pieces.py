"""Apply the frozen native candidate semantic_pm2_named_pieces."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_named_pieces"
down_revision = "semantic_pm2_condition_admission"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_named_pieces_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "4092dd90337c7ddc0faf4deb60d3716cb925b10e7c50a1a9cf1d618b991a6ba9"
NATIVE_STATE_FILE = "semantic_pm2_named_pieces_native.json"
NATIVE_STATE_SHA256 = "fed8396e8210f5e27705d91adaae166418a6e5ee1844fce116ad154c6fca781e"
NATIVE_ADMISSION_FILE = "semantic_pm2_named_pieces_admission.sql"
NATIVE_ADMISSION_SHA256 = "894c9b3a760bb4af6b495ae2bc891525d8d439b1c70ac180532a8c019a0df754"


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
