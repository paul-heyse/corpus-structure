"""Apply the frozen native candidate semantic_ddo_pe_n32."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n32"
down_revision = 'semantic_ddo_pe_n31'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n32_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "98034b0ce41be5d474decdd8b7b27a4a3e44d43109abaa558ad9a9ec382dd537"
NATIVE_STATE_FILE = "semantic_ddo_pe_n32_native.json"
NATIVE_STATE_SHA256 = "23b84d5f6ea1dbb16b1624001c11819967d51cd0c570e38b05d511caea6e9b7f"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n32_admission.sql"
NATIVE_ADMISSION_SHA256 = "e6cfcdf3a34334654bc4f2df87e1d617b37663591e8a791d0bcbbce87beb65d9"


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
