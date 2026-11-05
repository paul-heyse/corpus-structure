"""Prepare local semantic publication witnesses once per native invocation; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_batch_20261105"
down_revision = "semantic_pce_ports_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_batch_20261105_native.json"
NATIVE_STATE_SHA256 = "5cc4cba77798436c29d14aaf0eae8a3c2232ffcd4cba6ae88d64d701d4932e51"
NATIVE_ADMISSION_FILE = "semantic_pce_batch_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "aaac3df058fe8d97724d4ec8033923c3ba1655e487d716cb267ee78de91b6faf"
NATIVE_UPGRADE_FILE = "semantic_pce_batch_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "4f8fa7739c1da8c390ab24934fc91357f392357177ece79e6895b50fa4b998b5"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen local publication artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible local publication predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive local publication downgrade refused")
