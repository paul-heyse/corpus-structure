"""Apply the frozen native candidate semantic_ddo_pe_n34."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n34"
down_revision = 'semantic_ddo_pe_n33'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n34_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "48053fc2ebceff534ab9cc43230f5dce6ff7754ec1971b1795b5f4b3cbe32e29"
NATIVE_STATE_FILE = "semantic_ddo_pe_n34_native.json"
NATIVE_STATE_SHA256 = "807ebc3cd0fa2cdb7cf5bfe3917a02c7ad55038a8bff399d3e55506dfef465c3"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n34_admission.sql"
NATIVE_ADMISSION_SHA256 = "db57ed4432f0e59514e6d8f4c4136128cdee5b1ea6ea3030787c20c624f46619"


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
