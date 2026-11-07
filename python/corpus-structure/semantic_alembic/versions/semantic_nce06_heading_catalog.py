"""Apply the frozen native candidate semantic_nce06_heading_catalog."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce06_heading_catalog"
down_revision = "semantic_nce06_heading_links"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce06_heading_catalog_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "fd54d274d2236a48a72d8a50b1223579c1100c0e2185748c5f7d21a184d3e751"
NATIVE_STATE_FILE = "semantic_nce06_heading_catalog_native.json"
NATIVE_STATE_SHA256 = "f942f2f1328146fbebf198d9bf7d4c37b8a702766c2fa57f9918c1ab40801145"
NATIVE_ADMISSION_FILE = "semantic_nce06_heading_catalog_admission.sql"
NATIVE_ADMISSION_SHA256 = "e12f23fa2ef49e180618d4e2d0bcd0f19cdd9620b7ae4048a1c01381f3711b5a"


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
