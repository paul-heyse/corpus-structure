"""Apply the frozen native candidate semantic_ddo_pe_n13."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n13"
down_revision = 'semantic_ddo_pe_n12'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n13_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "100f4cb9b3c2ae24bb08b7fa182c44d5b9c30608a5db04cc5c66ecf48dc86f30"
NATIVE_STATE_FILE = "semantic_ddo_pe_n13_native.json"
NATIVE_STATE_SHA256 = "a7c3a45e54260a923ae68ba2c68632c64b4b37a90ea27c29c637024db6b5959a"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n13_admission.sql"
NATIVE_ADMISSION_SHA256 = "2e15274dc59cb96eaa45811eba1b15b5c13ee7a2eb43954249cb8517db8431fb"


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
