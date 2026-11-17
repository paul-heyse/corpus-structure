"""Apply the frozen native candidate semantic_ddo_policy_json."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_policy_json"
down_revision = 'semantic_ddo_selected_proofs'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_policy_json_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "5c7a74c565efea333f125565b1d842a20655fe9d05bf77334aab82bf6fd0cbe8"
NATIVE_STATE_FILE = "semantic_ddo_policy_json_native.json"
NATIVE_STATE_SHA256 = "f4df63cca0acd318842d15cc58c63eb9f0ba589bb8e54f9ec866f9355943afe6"
NATIVE_ADMISSION_FILE = "semantic_ddo_policy_json_admission.sql"
NATIVE_ADMISSION_SHA256 = "0df88eea1897824b7a71cba6094d0c33fc825ab2148e544b1ba74cf29c1ba346"


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
