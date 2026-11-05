"""Bind automatic definition result dimensions."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_defbind_20261105"
down_revision = "semantic_pce_defauto_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_defbind_20261105_native.json"
NATIVE_STATE_SHA256 = "7dea1828df1b99dd8212a0cd7bd4437cd8cc4f44d45b0ef8efaaef1947c86ac9"
NATIVE_ADMISSION_FILE = "semantic_pce_defbind_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "23f68527089de1b469e3082b9182daa6f5f08536bf61bbffeea6ac2b59345ce7"
NATIVE_UPGRADE_FILE = "semantic_pce_defbind_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "0e6cecf20f55d6a6a6ee19f560e6a363957557079b8d7ab8a7d110045ff5bb18"


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
