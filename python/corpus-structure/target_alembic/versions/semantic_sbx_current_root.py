"""Apply the frozen native candidate semantic_sbx_current_root."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_current_root"
down_revision = None
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_current_root_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "3859d43349f0837696fe667a80448786691086b2c24bba3b2c2cb7d7d2a53a78"
NATIVE_STATE_FILE = "semantic_sbx_current_root_native.json"
NATIVE_STATE_SHA256 = "1f041e9d3a0698fd5bf11085a4dfd6910551e9362ccaa77ee569a9a75cc69861"
NATIVE_ADMISSION_FILE = "semantic_sbx_current_root_admission.sql"
NATIVE_ADMISSION_SHA256 = "75dbc35d832ea6e628f63bcad2c21af03bb1d89711a207e18339ff6e3af9ae53"


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
