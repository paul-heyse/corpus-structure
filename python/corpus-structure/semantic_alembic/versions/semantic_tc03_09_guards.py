"""Apply the frozen native candidate semantic_tc03_09_guards."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc03_09_guards"
down_revision = "semantic_tc03_09_primary"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc03_09_guards_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "6c0173a2d5f89e820e311d4d9582e868555e36fca7c4a2a591eb74c0ee53f0b8"
NATIVE_STATE_FILE = "semantic_tc03_09_guards_native.json"
NATIVE_STATE_SHA256 = "8d0aa6f6d635818527dbfe9c081b91a39b285f504ad6d99b29f70e89c3e79e5b"
NATIVE_ADMISSION_FILE = "semantic_tc03_09_guards_admission.sql"
NATIVE_ADMISSION_SHA256 = "c19c92f8ad44085acc84a816f80c7db9d4f5269d17e44b6ed3d3fba8a0a65326"


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
