"""Apply the frozen native candidate semantic_ddo_stream_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_stream_v1"
down_revision = "semantic_ddo_projection_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_stream_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "71b6780a73a9da3939068564e7ca0ead077de1ed17d91eb4f7a8b8e4a3da64ca"
NATIVE_STATE_FILE = "semantic_ddo_stream_v1_native.json"
NATIVE_STATE_SHA256 = "e06e90d8671530f14b80c3eddd9c980118044bdf7677670da0aa24df727c8b8d"
NATIVE_ADMISSION_FILE = "semantic_ddo_stream_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "1865882ff4ab9a911af853a6acb96f9de2cad6df1ad7a67b61c5c6fc42dcd872"


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
