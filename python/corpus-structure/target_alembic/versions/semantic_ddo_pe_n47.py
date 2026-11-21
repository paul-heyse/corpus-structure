"""Apply the frozen native candidate semantic_ddo_pe_n47."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n47"
down_revision = 'semantic_ddo_pe_n46'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n47_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "17c949d6f2f78f886acbfe56212777aafb3ba0db87064215852f7cec46641edf"
NATIVE_STATE_FILE = "semantic_ddo_pe_n47_native.json"
NATIVE_STATE_SHA256 = "d920a1538a3fcad84a506ed0f042bc7dc4ff364b985e753758c35332d3e886b7"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n47_admission.sql"
NATIVE_ADMISSION_SHA256 = "fc76cf508e81fd4120bc13543e0b11b1e3e1fa14c7f941a498bba7daad77f3b1"


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
