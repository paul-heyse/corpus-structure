"""Apply the frozen native candidate semantic_bep_located_v2."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_bep_located_v2"
down_revision = "semantic_tc_choice_assessment"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_bep_located_v2_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e630094a08a02e692e8a01ec318456007553dd2e5450c6cd34e2eb6a3aaa1490"
NATIVE_STATE_FILE = "semantic_bep_located_v2_native.json"
NATIVE_STATE_SHA256 = "1d294f27c0bc22a379d477c8e1b6e255ccdb835ce6685d15aa8df11d5ee996b4"
NATIVE_ADMISSION_FILE = "semantic_bep_located_v2_admission.sql"
NATIVE_ADMISSION_SHA256 = "4e1a41c37205ce3ad5a6de9c4a5fec701cef0cc1cc096c09015d83f1b852fdff"


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
