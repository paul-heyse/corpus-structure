"""Apply the frozen native candidate semantic_nce_audit_fit_guard."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_audit_fit_guard"
down_revision = "semantic_nce_audit_closure"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_audit_fit_guard_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "f0c240e827af735b767123790911ed10799d4e06e3a15ee7be116a2a68a99b61"
NATIVE_STATE_FILE = "semantic_nce_audit_fit_guard_native.json"
NATIVE_STATE_SHA256 = "94a170d157aa4d3fb09ffb4ba6719be5cd929c73f6ba5e5e0750842349ec312a"
NATIVE_ADMISSION_FILE = "semantic_nce_audit_fit_guard_admission.sql"
NATIVE_ADMISSION_SHA256 = "93ddcd325507a4826aeb3d89f6c342c15411192903936ec001483e09c3e42f97"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
