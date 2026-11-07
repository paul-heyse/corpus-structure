"""Apply the frozen native candidate semantic_nce03_06_model_fence."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce03_06_model_fence"
down_revision = "semantic_nce03_06_witnessed"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce03_06_model_fence_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d6e165847deda89b7232deb478fe073a5ae77a7e2a19cf3f3bef84c0578664f0"
NATIVE_STATE_FILE = "semantic_nce03_06_model_fence_native.json"
NATIVE_STATE_SHA256 = "331d2f321ba95f094d7fa8ddc1c44cad7cf4225d6b564e38d4100f77d1497a84"
NATIVE_ADMISSION_FILE = "semantic_nce03_06_model_fence_admission.sql"
NATIVE_ADMISSION_SHA256 = "65138fafd72c0c263c94565bf5e0250cac00dda2a7ccaeecdc621d76de5e964c"


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
