"""Apply the frozen native candidate semantic_tc02_reachability."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc02_reachability"
down_revision = "semantic_tc02_cross_release"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc02_reachability_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "1e8fc4fd234cda99124c278349ca90c277f4ec9f1f971cfa368f54f7bd4d1af3"
NATIVE_STATE_FILE = "semantic_tc02_reachability_native.json"
NATIVE_STATE_SHA256 = "23f036d738d7a45ff121fd84eb85a9145d01bdb1bc9c3200a899ad4acddd9a29"
NATIVE_ADMISSION_FILE = "semantic_tc02_reachability_admission.sql"
NATIVE_ADMISSION_SHA256 = "9ca77d197db4ff06985fcb0ef1412e7025573fef965f2379dad33f0ad8473cff"


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
