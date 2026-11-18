"""Apply the frozen native candidate semantic_ddo_pe_n23."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n23"
down_revision = 'semantic_ddo_pe_n22'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n23_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "3a6b9a9e9b1fb592a72a1bf1643cb3dc259fca519e505c896a5b4f079fb2b1be"
NATIVE_STATE_FILE = "semantic_ddo_pe_n23_native.json"
NATIVE_STATE_SHA256 = "c6aefaebb10cd6e027c4f8e22bc309e8ce1f94755e88d495b24ee5d61eca2766"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n23_admission.sql"
NATIVE_ADMISSION_SHA256 = "d7e2db1d8f9eed36391e1074bb88cca04b73b6dcc9a073bf7c64414d9c2b0b79"


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
