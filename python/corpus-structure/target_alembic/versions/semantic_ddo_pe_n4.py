"""Apply the frozen native candidate semantic_ddo_pe_n4."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n4"
down_revision = 'semantic_ddo_pe_n3'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n4_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "62cfc333170f779e823e0ca7f28d15e73ecf1f6e3a85633d5c96831b30cdd955"
NATIVE_STATE_FILE = "semantic_ddo_pe_n4_native.json"
NATIVE_STATE_SHA256 = "6a2491dfb0d1b12661a71e37517b92fc52c495f27eff4702d36ab3947bb7dfe0"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n4_admission.sql"
NATIVE_ADMISSION_SHA256 = "61124fae28b65eafa71eb6a9e56c595247fe1bd6804dcba533b0e8da8eb7d571"


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
