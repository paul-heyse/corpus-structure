"""Apply the frozen native candidate semantic_ddo_pe_n45."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n45"
down_revision = 'semantic_ddo_pe_n44'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n45_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "886cfac0275e6a09ea671ba4d1245c175bca5ae361993d8ce70d69166fbbd32e"
NATIVE_STATE_FILE = "semantic_ddo_pe_n45_native.json"
NATIVE_STATE_SHA256 = "032454acd1dae6c26eedf46647b36134968ca9161a9fd466c58dec2b6f33b9b2"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n45_admission.sql"
NATIVE_ADMISSION_SHA256 = "9d1090e2bc33a8dce2e0b132e7d3d37dbbc1d5daa163c2662c7a70202157e1c0"


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
        admit_privileges(
            op.get_bind(), state["privileges"],
            purpose_roles=state.get("privilege_purpose_roles"),
        )


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
