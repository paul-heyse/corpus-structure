"""Apply the frozen native candidate semantic_ddo_kernel_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_kernel_v1"
down_revision = "semantic_bep_located_v2"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_kernel_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "56663896be32a8af822814a55f632676f67b46af5c9edee85e56ea14207f7c38"
NATIVE_STATE_FILE = "semantic_ddo_kernel_v1_native.json"
NATIVE_STATE_SHA256 = "f4dbd0815f504397b5a5ca89a7d7ec0da3b1dd79a9396a45dc5a382b04fee439"
NATIVE_ADMISSION_FILE = "semantic_ddo_kernel_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "4f81819f48986f61199728f15600c9d0499d03019b8b20f5575e1bc22192bcda"


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
