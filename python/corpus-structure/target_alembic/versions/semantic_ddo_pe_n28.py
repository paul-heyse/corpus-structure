"""Apply the frozen native candidate semantic_ddo_pe_n28."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n28"
down_revision = 'semantic_ddo_pe_n27'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n28_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e7b8931b41af8034767107c9a68ec298d1ff024c57a680bfdb834d8e6700756f"
NATIVE_STATE_FILE = "semantic_ddo_pe_n28_native.json"
NATIVE_STATE_SHA256 = "0f07dd3b88c057172b61a7d9f6baa915ff88f2cd6e118da1a2277e3e45878559"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n28_admission.sql"
NATIVE_ADMISSION_SHA256 = "2327854dffb04c5c35cab305843882db8ec5b043c68f25bc7468a3130848a5fb"


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
