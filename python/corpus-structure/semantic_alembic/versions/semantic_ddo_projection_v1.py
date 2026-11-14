"""Apply the frozen native candidate semantic_ddo_projection_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_projection_v1"
down_revision = "semantic_test_pdf_seal_producer"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_projection_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "68b64d32e3e423ec48628494726b83172fef3d3e537f2d7016c6b0b4e73a543a"
NATIVE_STATE_FILE = "semantic_ddo_projection_v1_native.json"
NATIVE_STATE_SHA256 = "bd7b64eb85805a9b5295b384f7ac9274dca42dd3b533b637cb79dfd5cfd0a3f3"
NATIVE_ADMISSION_FILE = "semantic_ddo_projection_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "8c2b042c59efcb22b3b440ccb600d2222221017e6a7ac685f9aa28d45ce08d01"


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
