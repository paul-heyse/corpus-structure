"""Apply the frozen native candidate semantic_ddo_pe_n39."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n39"
down_revision = 'semantic_ddo_pe_n38'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n39_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "be26b5b4defe890e822766f143840184240f3f50e7a849c1ba473a61940198a3"
NATIVE_STATE_FILE = "semantic_ddo_pe_n39_native.json"
NATIVE_STATE_SHA256 = "b47763a44b61e931c9303632bc4b2afcb7a8f9ed09ea20cbf03ccfd74611b54f"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n39_admission.sql"
NATIVE_ADMISSION_SHA256 = "f353910a4b2fde2e2c869be1acaac2295c1374d3c1e5e65a9b4c77e7e35b1b10"


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
