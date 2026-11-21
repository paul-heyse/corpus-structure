"""Apply the frozen native candidate semantic_ddo_pe_n44."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n44"
down_revision = 'semantic_ddo_pe_n43'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n44_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "99e7509ca2adcb00713d718b6f1a9e60dd020bbae65ea97926c7e9b454fa2bab"
NATIVE_STATE_FILE = "semantic_ddo_pe_n44_native.json"
NATIVE_STATE_SHA256 = "1dc819f7bde9074ed9e53eebad31e6462fb101573038fa871d9777f01f608e9f"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n44_admission.sql"
NATIVE_ADMISSION_SHA256 = "8111daf655150d1f38b02f22d45bd23909d23c8480f6f015ab41425fb8206502"


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
