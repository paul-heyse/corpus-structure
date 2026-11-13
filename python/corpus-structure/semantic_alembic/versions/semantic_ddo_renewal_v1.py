"""Apply the frozen native candidate semantic_ddo_renewal_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_renewal_v1"
down_revision = "semantic_ddo_recovery_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_renewal_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "f8082ecfe98333d04ed1a1d07c92635a3ce607fd6bb2bed3ac8cd2383187f9cd"
NATIVE_STATE_FILE = "semantic_ddo_renewal_v1_native.json"
NATIVE_STATE_SHA256 = "01c04ab9d7bec5886561f009cb81b1d96daf03c1e89c0f2198a82f11b06a162b"
NATIVE_ADMISSION_FILE = "semantic_ddo_renewal_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "4d9d8a16d116c82006850caa6ba90bc2e543dfe2785ed67eb2cdb45ed3dca4d6"


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
