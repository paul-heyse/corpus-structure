"""Apply the frozen native candidate semantic_ddo_pe_n41."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n41"
down_revision = 'semantic_ddo_pe_n40'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n41_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d69b5be76c1fd297fa202cd37ded956cbed0817f7bf3bde5548577056249f144"
NATIVE_STATE_FILE = "semantic_ddo_pe_n41_native.json"
NATIVE_STATE_SHA256 = "62dfbd4c289887642e0ee06802d79db28b17810b736a00887289d8c0dc1b0502"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n41_admission.sql"
NATIVE_ADMISSION_SHA256 = "d5a2e8d660a305ce12a7310da29185bea6d93f16732cccb4d627cf243ee7fb58"


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
