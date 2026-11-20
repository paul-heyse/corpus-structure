"""Apply the frozen native candidate semantic_ddo_pe_n37."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n37"
down_revision = 'semantic_ddo_pe_n36'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n37_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "f8bb18ce9bc6106535c7922860f1a699800c5918341e7b3a77fa45b42a423568"
NATIVE_STATE_FILE = "semantic_ddo_pe_n37_native.json"
NATIVE_STATE_SHA256 = "e7c10e8cb6d7840880ef449d1686a61da138ef41c17e96df840f8f97043b7feb"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n37_admission.sql"
NATIVE_ADMISSION_SHA256 = "65d5360319bc696c3f32da2fadab9dcd719b64af7db37d438a0c3f3e76dd63fb"


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
