"""Apply the frozen native candidate semantic_sbx_current_root."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_current_root"
down_revision = None
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_current_root_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "12866f5ca29eafa500ac9ba98482a133a578148764e01f6ee18713a3dd4976df"
NATIVE_STATE_FILE = "semantic_sbx_current_root_native.json"
NATIVE_STATE_SHA256 = "5df8acc9c51e745ced9d4c107fe645be7025b3ba9172d43df91be0473cf4e2f5"
NATIVE_ADMISSION_FILE = "semantic_sbx_current_root_admission.sql"
NATIVE_ADMISSION_SHA256 = "0d103a8600d179b2e43178c4204c58f7bf01eb929965b9288e35a66acb3ec890"


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
