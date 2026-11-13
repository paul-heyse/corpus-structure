"""Apply the frozen native candidate semantic_ddo_recovery_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_recovery_v1"
down_revision = "semantic_ddo_kernel_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_recovery_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "f8f9cfbb8baba53aa50c5d5443e8da78ad36705900b6873ea1cf63a0b830057e"
NATIVE_STATE_FILE = "semantic_ddo_recovery_v1_native.json"
NATIVE_STATE_SHA256 = "a75491a0cc380a96196179cd462991532cf024dad77a52b2b3421575ed68da9e"
NATIVE_ADMISSION_FILE = "semantic_ddo_recovery_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "347e69083f8c359897fbb21da5deb96732ee78e5a0a986a477c641e6f48781fc"


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
