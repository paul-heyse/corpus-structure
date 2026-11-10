"""Apply the frozen native candidate semantic_ptd_runtime_compiler."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ptd_runtime_compiler"
down_revision = "semantic_ptd_typed_bindings"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ptd_runtime_compiler_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "a37b58af9cc22354aa5a3c4a65df169d6e98e8625578f4e315828cf306b94ff4"
NATIVE_STATE_FILE = "semantic_ptd_runtime_compiler_native.json"
NATIVE_STATE_SHA256 = "dd2c4db8c111bf4fd426fd2cd36005dc778bb820ef038a914fb5a1af78f884e6"
NATIVE_ADMISSION_FILE = "semantic_ptd_runtime_compiler_admission.sql"
NATIVE_ADMISSION_SHA256 = "3f1855f017e1eb26c82ea2c9a52b51cc68ca4619bb6674c849d36e0cf6fca908"


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
