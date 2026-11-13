"""Apply the frozen native candidate semantic_ddo_archive_v5."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_archive_v5"
down_revision = "semantic_ddo_archive_v4"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_archive_v5_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "3f596aa7dd7df331a05a668e633d9e97459f4352dc84fb89897917177f321f16"
NATIVE_STATE_FILE = "semantic_ddo_archive_v5_native.json"
NATIVE_STATE_SHA256 = "10138feb9ac47ea73215d9c2fc7cdd1c31d0bbf9231fb1c4ffcc49054d838869"
NATIVE_ADMISSION_FILE = "semantic_ddo_archive_v5_admission.sql"
NATIVE_ADMISSION_SHA256 = "a69d1c3cf24ea1c2a43fb54084f0013b8e5d697a301fe09dee806918028a0556"


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
