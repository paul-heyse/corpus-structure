"""Apply the frozen native candidate semantic_nce07_12_replay."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce07_12_replay"
down_revision = "semantic_nce07_12"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce07_12_replay_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "b85884a1ef02c44669b6524b730838cda6671ab9e803a57cb4815e418b607272"
NATIVE_STATE_FILE = "semantic_nce07_12_replay_native.json"
NATIVE_STATE_SHA256 = "d19b9fecd233e34dd4a82863fb1da6bf1d579fa9696286934ebb530f1f2d9e84"
NATIVE_ADMISSION_FILE = "semantic_nce07_12_replay_admission.sql"
NATIVE_ADMISSION_SHA256 = "9c51a396086c8c08237a7f36af647cde5d5a81cb18a281b427cb01e1b242a0eb"


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
