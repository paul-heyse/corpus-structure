"""Apply the frozen native candidate semantic_nce_audit_blocks."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_audit_blocks"
down_revision = "semantic_nce_audit_governors"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_audit_blocks_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e1ed708acdb95eb790d45610deae9422dff3fea8cb8aa69e8b76abb8d69171d1"
NATIVE_STATE_FILE = "semantic_nce_audit_blocks_native.json"
NATIVE_STATE_SHA256 = "d36f2dde9b2830a14d93229eb9fc012e7174abc91ed4e88b3743e3ae0f6d6af6"
NATIVE_ADMISSION_FILE = "semantic_nce_audit_blocks_admission.sql"
NATIVE_ADMISSION_SHA256 = "e439937c4b2e1a5d475a9b3726df50025eb29a966764c1b76fd7a0bfcc9001c9"


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
