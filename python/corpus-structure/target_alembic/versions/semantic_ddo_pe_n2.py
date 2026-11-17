"""Apply the frozen native candidate semantic_ddo_pe_n2."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n2"
down_revision = 'semantic_ddo_pe_n1'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n2_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "2965fe5d0b0ad16505720eedf9ac1508994837337189783a506f7d406a9ebd18"
NATIVE_STATE_FILE = "semantic_ddo_pe_n2_native.json"
NATIVE_STATE_SHA256 = "33eb4a5d129f5219712266e360a3c57aed2816a62594f803f05ed368d5ae7c8f"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n2_admission.sql"
NATIVE_ADMISSION_SHA256 = "59b5f01d17f322122fea91fd4dfd31a4c69ea87b0f142ebad35241dd2f2ac896"


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
