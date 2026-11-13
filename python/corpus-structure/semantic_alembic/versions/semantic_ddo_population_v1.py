"""Apply the frozen native candidate semantic_ddo_population_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_population_v1"
down_revision = "semantic_ddo_renewal_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_population_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "2f2ddb1313df46010125c2eba11d189daa122aa1d678bffb33fd29312c106622"
NATIVE_STATE_FILE = "semantic_ddo_population_v1_native.json"
NATIVE_STATE_SHA256 = "f38027f4d816b15f01ad34aa4788386a89453755e9df369cdce41334fb23719f"
NATIVE_ADMISSION_FILE = "semantic_ddo_population_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "c3ac29804b51f2a68873a98bf4aa44b71f38d8f4e083c013b14acabad0f96642"


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
