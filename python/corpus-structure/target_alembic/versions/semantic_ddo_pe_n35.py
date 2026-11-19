"""Apply the frozen native candidate semantic_ddo_pe_n35."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n35"
down_revision = 'semantic_ddo_pe_n34'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n35_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "7b18f154df7c6b33e46435ad726157dc8edea60b26975a3140ecac377af730d1"
NATIVE_STATE_FILE = "semantic_ddo_pe_n35_native.json"
NATIVE_STATE_SHA256 = "a92ecf7df9c28ede276da0239c414a9da478f172ea279b7c2d0d0aed6cdaca7b"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n35_admission.sql"
NATIVE_ADMISSION_SHA256 = "1026161180713e4cbd0d1b07702dcbe5bf56b76da40b90bc96a7163e27b08f11"


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
