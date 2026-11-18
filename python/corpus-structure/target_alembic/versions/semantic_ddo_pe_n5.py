"""Apply the frozen native candidate semantic_ddo_pe_n5."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n5"
down_revision = 'semantic_ddo_pe_n4'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n5_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "0cd61879ddbd9e6c2b2751123ba613559a45b977485225414ae43f3107ca4a81"
NATIVE_STATE_FILE = "semantic_ddo_pe_n5_native.json"
NATIVE_STATE_SHA256 = "73eef5c25adc129bf80b3e12cf699f46ddba0fa85aaf8f027767ce5ebbc7a87c"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n5_admission.sql"
NATIVE_ADMISSION_SHA256 = "b6a9c805247bcacba727cfddc91606c77ee045c169231b712e43269d63e7c284"


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
