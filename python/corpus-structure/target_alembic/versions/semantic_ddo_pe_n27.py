"""Apply the frozen native candidate semantic_ddo_pe_n27."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n27"
down_revision = 'semantic_ddo_pe_n26'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n27_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "c488890cdd66efd796bd756a3c367b4b2384c35edef1bc5fdc077cf49c9e7f23"
NATIVE_STATE_FILE = "semantic_ddo_pe_n27_native.json"
NATIVE_STATE_SHA256 = "6d44c8de275a05eaf2a593cdd5c73bb6d523a7d94854b64a0caf654f98657925"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n27_admission.sql"
NATIVE_ADMISSION_SHA256 = "adeb7ee9b94557b701904a443c7b53100570cbc2a3a7aed2bb547107d2ba1481"


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
