"""Apply the frozen native candidate semantic_ddo_pe_n40."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n40"
down_revision = 'semantic_ddo_pe_n39'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n40_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "237af8fed369a3be4e08de338eb21bc9be38d75ef0c3f2cb824d24cfda1e29d5"
NATIVE_STATE_FILE = "semantic_ddo_pe_n40_native.json"
NATIVE_STATE_SHA256 = "b796fa2250c86f8b4719788db896f45bccc79541d2f4c1596dbb1dae35688a5f"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n40_admission.sql"
NATIVE_ADMISSION_SHA256 = "1c4a6785623849df9d89fe16eb9ccce896de45fb898c3049bc8bfa236435df1f"


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
