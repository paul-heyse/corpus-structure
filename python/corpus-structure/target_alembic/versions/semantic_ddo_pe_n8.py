"""Apply the frozen native candidate semantic_ddo_pe_n8."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n8"
down_revision = 'semantic_ddo_pe_n7'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n8_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "171a1d8474f6498fac9d6b0c3679ae61e4eb53adbfbeb2f065e19692941376b8"
NATIVE_STATE_FILE = "semantic_ddo_pe_n8_native.json"
NATIVE_STATE_SHA256 = "21923c057e9fc729e3e6c13aac4a5cf430d19ff16581e8d4abafe5fa4134108d"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n8_admission.sql"
NATIVE_ADMISSION_SHA256 = "d93b6b16e117d39bfb7439c87507ad6a10fb75880bdb7ef8a39d748994a5e261"


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
