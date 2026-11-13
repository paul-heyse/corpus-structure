"""Apply the frozen native candidate semantic_ddo_archive_v3."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_archive_v3"
down_revision = "semantic_ddo_archive_v2"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_archive_v3_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e0da5f42ff71a2f875588a107b296f5665ee39f6bbc5957191fce97d106966e5"
NATIVE_STATE_FILE = "semantic_ddo_archive_v3_native.json"
NATIVE_STATE_SHA256 = "c1ccdd0139d800f3e60fb40c5a72470150c916ad7b1e1e41108920cf0ac463e7"
NATIVE_ADMISSION_FILE = "semantic_ddo_archive_v3_admission.sql"
NATIVE_ADMISSION_SHA256 = "fba05aa42f2629ecdc4a978f9777de054e47378c6399cbd5ab66134ed6abb9c6"


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
