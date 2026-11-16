"""Apply the frozen native candidate semantic_ddo_stable_read_renewal."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_stable_read_renewal"
down_revision = 'semantic_ddo_observation_split'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_stable_read_renewal_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e19ebf42de830e74c4d75fc7780ba2a446a7dc206b9de0de2a94b3279a253813"
NATIVE_STATE_FILE = "semantic_ddo_stable_read_renewal_native.json"
NATIVE_STATE_SHA256 = "f4fecfb977c66e7bae91005319e29ba74bbc2fdb0cc2623ad40d6931824a8609"
NATIVE_ADMISSION_FILE = "semantic_ddo_stable_read_renewal_admission.sql"
NATIVE_ADMISSION_SHA256 = "8491b90790c4b996b0db2747526e39bd46fae54608744dcf0fcb583d2d7d376e"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 2 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))
    if state["version"] == 2:
        from corpus_structure.semantic.alembic_privileges import admit_privileges
        admit_privileges(op.get_bind(), state["privileges"])


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
