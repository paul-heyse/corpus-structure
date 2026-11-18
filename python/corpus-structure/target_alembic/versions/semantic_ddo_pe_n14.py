"""Apply the frozen native candidate semantic_ddo_pe_n14."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n14"
down_revision = 'semantic_tdm_pdf_stream_protocol'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n14_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "7fc1a8d773227b6aefbeb3264afd2b844659369c88e89d3d9f4ae6244f8fecd0"
NATIVE_STATE_FILE = "semantic_ddo_pe_n14_native.json"
NATIVE_STATE_SHA256 = "63ea46da647d34cb2e2c039e52a57d751920d5e196b6fe5e0eb19705ac931a86"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n14_admission.sql"
NATIVE_ADMISSION_SHA256 = "fc117afbfae4eb89e6316be9bdc76f66f36b0f744df719df32df6a26e6ded620"


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
