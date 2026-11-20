"""Apply the frozen native candidate semantic_ddo_pe_n43."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n43"
down_revision = 'semantic_ddo_pe_n42'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n43_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "4a98eada0495ada86adfda002247ffafe7a1b0b45c2804a24c87411e6acc6c04"
NATIVE_STATE_FILE = "semantic_ddo_pe_n43_native.json"
NATIVE_STATE_SHA256 = "fe87a5660bba26dd7ec6787643558b8171da8495dccb491b311da5bc9e3989f4"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n43_admission.sql"
NATIVE_ADMISSION_SHA256 = "52e0a4a4a1ae6d3649bf5ada2368884a536fad3c8fb6169f8262e3a0e0517b8e"


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
