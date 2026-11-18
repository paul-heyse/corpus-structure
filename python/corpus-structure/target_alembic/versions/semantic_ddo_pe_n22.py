"""Apply the frozen native candidate semantic_ddo_pe_n22."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n22"
down_revision = 'semantic_ddo_pe_n21'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n22_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "84f81c3af483b76a30ca27f0ff23a1335e3416ca39d569d69e1919c1e512775e"
NATIVE_STATE_FILE = "semantic_ddo_pe_n22_native.json"
NATIVE_STATE_SHA256 = "a595df4d70be82fe20cde1230b49d1823293cbc74a9d52ecc3e805add7b0c9ef"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n22_admission.sql"
NATIVE_ADMISSION_SHA256 = "a4d5a88e7f6f2b55874ec75faaba8569890456110b97668e8af9ef1da5ddb529"


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
