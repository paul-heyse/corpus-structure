"""Apply the frozen native candidate semantic_nce06_heading_release."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce06_heading_release"
down_revision = "semantic_nce06_heading_catalog"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce06_heading_release_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "a9ae15ecb22e11f49cca4d7bb413f3523e40bbd3c769fdb2ddd891a3b0ff1870"
NATIVE_STATE_FILE = "semantic_nce06_heading_release_native.json"
NATIVE_STATE_SHA256 = "55cebb06bfb132dc395eddca6be7581eb0c60b344d4d3cf10dc05fd24e23f572"
NATIVE_ADMISSION_FILE = "semantic_nce06_heading_release_admission.sql"
NATIVE_ADMISSION_SHA256 = "39bb90f7cae359c0935e5fc5b53c7e782a8a8d00d998024b06ee1ee62828271b"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
