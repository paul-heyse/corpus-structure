"""Apply the frozen native candidate semantic_ddo_pe_n30."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n30"
down_revision = 'semantic_ddo_pe_n29'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n30_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "c84277997dc0d075558dd078365da3e851c46714df4f2f8f1e778e7318679f21"
NATIVE_STATE_FILE = "semantic_ddo_pe_n30_native.json"
NATIVE_STATE_SHA256 = "ce81c9e676a9294e25999a0e2c8f8b8874b5b126d89d5f3f863898965cf3f76c"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n30_admission.sql"
NATIVE_ADMISSION_SHA256 = "a5ac8ed81810c6884f3cdf1039a86a6d62e0cda41c1a2576ee2ed32535a607f1"


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
