"""Apply the frozen native candidate semantic_ddo_archive_v2."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_archive_v2"
down_revision = "semantic_ddo_original_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_archive_v2_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "239c973c82516a5aaa7f0e6909ae38a3fd4528e4efc7ecdc06876109b5512b47"
NATIVE_STATE_FILE = "semantic_ddo_archive_v2_native.json"
NATIVE_STATE_SHA256 = "af7c56c99f4a9c460adfa59020ac88aa7379479483fdc65b129559ead2d1ccaa"
NATIVE_ADMISSION_FILE = "semantic_ddo_archive_v2_admission.sql"
NATIVE_ADMISSION_SHA256 = "963c3d3e9900edeb9e53285cf5cb69a4a56da6ce6798d265917c798379dc1112"


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
