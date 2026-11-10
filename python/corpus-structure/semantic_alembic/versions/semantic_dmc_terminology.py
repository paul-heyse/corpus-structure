"""Apply the frozen native candidate semantic_dmc_terminology."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_dmc_terminology"
down_revision = "semantic_dmc_compiler20"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_dmc_terminology_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "2dbf90d16276f79bab2852dfb8e645c880209ae133b2ca7b95273e8f4e62cc3c"
NATIVE_STATE_FILE = "semantic_dmc_terminology_native.json"
NATIVE_STATE_SHA256 = "49e4636554e4a77385012334e9a1ed5a431d1b7ec4f17de06b0e3a9be6bc89a7"
NATIVE_ADMISSION_FILE = "semantic_dmc_terminology_admission.sql"
NATIVE_ADMISSION_SHA256 = "4c31aaf6f8722cd3afe2d00c77b5417751d08c3c82c0abe5d6795e97de7b1590"


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
