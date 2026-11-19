"""Apply the frozen native candidate semantic_ddo_pe_n36."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n36"
down_revision = 'semantic_ddo_pe_n35'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n36_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "5d71f89a26f6f45c5846ab5089f96dbb151819d2cfc2f817b5185e395e0a1319"
NATIVE_STATE_FILE = "semantic_ddo_pe_n36_native.json"
NATIVE_STATE_SHA256 = "cc27833c06720386034bd8d709677e732a690eead1dafebe3b81a0b7f4912785"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n36_admission.sql"
NATIVE_ADMISSION_SHA256 = "7d4ae5fda0dc1f161ff7334e4e06d7ef183b4a4b2b227fdc299e6e11ef845a38"


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
