"""Apply the frozen native candidate semantic_ddo_pe_n33."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n33"
down_revision = 'semantic_ddo_pe_n32'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n33_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e97cdd51146ac6805c3bc1403c4c9be833dd2fe09f917354d8c3cfccd7c9a870"
NATIVE_STATE_FILE = "semantic_ddo_pe_n33_native.json"
NATIVE_STATE_SHA256 = "a5e30e26307bbd7594da5f09dead73d3f1e2f060178aee5d7fcbf54d43d0fdd9"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n33_admission.sql"
NATIVE_ADMISSION_SHA256 = "63ccf306f8e3f9e89356f4728dc4b41339128d175abc53acfd2ad7e990f9576d"


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
