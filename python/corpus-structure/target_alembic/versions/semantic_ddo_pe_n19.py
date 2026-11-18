"""Apply the frozen native candidate semantic_ddo_pe_n19."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n19"
down_revision = 'semantic_ddo_pe_n18'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n19_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "ae7a7e09854245e20dd6278fed5ac0e08d708a118d4bedf10a68633b40e6bf53"
NATIVE_STATE_FILE = "semantic_ddo_pe_n19_native.json"
NATIVE_STATE_SHA256 = "32aaef941d45fabf3f274078217223c962d1ae758743a42614c9c660d1df1c46"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n19_admission.sql"
NATIVE_ADMISSION_SHA256 = "79c5db4bf92129ccfd31444f0c2aede0ed69f30836be4e87c715893624832b6b"


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
