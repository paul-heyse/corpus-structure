"""Apply the frozen native candidate semantic_nce06_heading_links."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce06_heading_links"
down_revision = "semantic_nce03_06_witness_fence"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce06_heading_links_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "23c127285661ec155b9e406acd7ffb87bebdd5d654f266ba29975e6133254674"
NATIVE_STATE_FILE = "semantic_nce06_heading_links_native.json"
NATIVE_STATE_SHA256 = "b6642823160538fb4691d9623e1f5fca3c243ff48c1f87a31a258a92cd53d6cf"
NATIVE_ADMISSION_FILE = "semantic_nce06_heading_links_admission.sql"
NATIVE_ADMISSION_SHA256 = "9cc8c7d2a51143340e0c4940d942ac4994abd82085886f6254596ebec71e1fe7"


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
