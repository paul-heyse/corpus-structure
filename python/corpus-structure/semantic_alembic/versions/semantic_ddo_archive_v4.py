"""Apply the frozen native candidate semantic_ddo_archive_v4."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_archive_v4"
down_revision = "semantic_ddo_archive_v3"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_archive_v4_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "b1d90962431c4f9f3e2017f5c92d618c585b89de98df18f8d2da26a77f7d135a"
NATIVE_STATE_FILE = "semantic_ddo_archive_v4_native.json"
NATIVE_STATE_SHA256 = "bd4d5eb42fd89796185b5dc3e338421512c3f19653fbeee2378809d0e2cf5930"
NATIVE_ADMISSION_FILE = "semantic_ddo_archive_v4_admission.sql"
NATIVE_ADMISSION_SHA256 = "e96f3a7e5c0cc04ffef62d321357198d41ba97b00c44e26bc82d6816176722ba"


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
