"""Apply the frozen native candidate semantic_ddo_pe_n38."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n38"
down_revision = 'semantic_ddo_pe_n37'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n38_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "11e0dde084b0a78d84840c7dd804163fe8e47d218a13aa43452ddae0c69591c6"
NATIVE_STATE_FILE = "semantic_ddo_pe_n38_native.json"
NATIVE_STATE_SHA256 = "719b9971f1d530585b2aebd41a3417e42df13f1ce6a7b9ea0a59ca38f1e0a01f"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n38_admission.sql"
NATIVE_ADMISSION_SHA256 = "cd2dab3c58453e15be044a449673e7c2825fa3a2567b1a9f94420e5fef73d5bb"


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
