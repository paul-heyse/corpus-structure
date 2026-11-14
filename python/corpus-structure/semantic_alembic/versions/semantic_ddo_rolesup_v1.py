"""Apply the frozen native candidate semantic_ddo_rolesup_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_rolesup_v1"
down_revision = "semantic_ddo_viewbind_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_rolesup_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "21a21dcbc9e8738f1bdced85d8beb8856c05dc57e0cbdc254dcc8831691eca5d"
NATIVE_STATE_FILE = "semantic_ddo_rolesup_v1_native.json"
NATIVE_STATE_SHA256 = "fc29cd9d9bef002bf79af2baf52189fdf87f6588d424aa653d79efddaeaf09eb"
NATIVE_ADMISSION_FILE = "semantic_ddo_rolesup_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "da0c6bf4c41cdcb2dd231e00a413405e58f935c3ea9d6fb3a391d2c057e3decc"


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
