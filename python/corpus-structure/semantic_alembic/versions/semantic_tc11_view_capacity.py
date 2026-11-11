"""Apply the frozen native candidate semantic_tc11_view_capacity."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc11_view_capacity"
down_revision = "semantic_tc10_11_ref_context"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc11_view_capacity_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "1e6d7df2e9160618f464695a2a43ad6c338b12cc38169f605d45a9cc2620b441"
NATIVE_STATE_FILE = "semantic_tc11_view_capacity_native.json"
NATIVE_STATE_SHA256 = "b1cd471d3adb7d92adb3c0c2d0a6536169350f99b2dc123ea37737c1d1bfeb40"
NATIVE_ADMISSION_FILE = "semantic_tc11_view_capacity_admission.sql"
NATIVE_ADMISSION_SHA256 = "3dc131a088fbf7b7ebd3dd0c2b38b07b480646ce95a91ca236aeaf08703a8189"


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
