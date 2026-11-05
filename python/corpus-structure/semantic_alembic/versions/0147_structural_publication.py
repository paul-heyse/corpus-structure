"""Publish structural statements and require committed exposure receipts."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_structpub_20261105"
down_revision = "semantic_pce_exposure_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_structpub_20261105_native.json"
NATIVE_STATE_SHA256 = "c3bf04626d5baae0495ce8ff6566c39728b22c853b2a7713287a72d5dafba8d2"
NATIVE_ADMISSION_FILE = "semantic_pce_structpub_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "479d51858ee35ef6a645cd4dce25fc09cfea0be1543bd4dae2cc64d50dc23f76"
NATIVE_UPGRADE_FILE = "semantic_pce_structpub_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "92467879a1d9bfc76a88505e981fd4077bd3c5a3e1bd4deb3b22156b78829ce8"


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
