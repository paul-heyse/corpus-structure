"""Apply the frozen native candidate semantic_ddo_pe_n46."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n46"
down_revision = 'semantic_ddo_pe_n45'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n46_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "3c6d208451c709187699d575202c8023e27dca1543b5d3617a4de3a80f9931b8"
NATIVE_STATE_FILE = "semantic_ddo_pe_n46_native.json"
NATIVE_STATE_SHA256 = "ea0434e3b6d42f2293d700d975a64803a0f5821f33a1709029ddb360e69182ef"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n46_admission.sql"
NATIVE_ADMISSION_SHA256 = "296b97c55ea355073d889727001c2bb42afcdf59b457650fd6c251554103646c"


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
