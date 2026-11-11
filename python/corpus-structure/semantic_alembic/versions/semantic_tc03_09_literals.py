"""Apply the frozen native candidate semantic_tc03_09_literals."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc03_09_literals"
down_revision = "semantic_tc03_09_carriers"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc03_09_literals_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "2edfdb8243370b92c4a2be74dcd4ac2591acad1e59155e01bc1d15e88ba97f57"
NATIVE_STATE_FILE = "semantic_tc03_09_literals_native.json"
NATIVE_STATE_SHA256 = "1a7b3ef85d92f81c4e87770d51185e763deef56098cc310fa969ec453f7f8335"
NATIVE_ADMISSION_FILE = "semantic_tc03_09_literals_admission.sql"
NATIVE_ADMISSION_SHA256 = "49bad037bec9c85dfe296933d426b4bcc32e8073efade5bac69ea94734fc6b9a"


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
