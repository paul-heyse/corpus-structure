"""Apply the frozen native candidate semantic_chandra_stage_schema."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_chandra_stage_schema"
down_revision = "semantic_chandra_inspection"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_chandra_stage_schema_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "3f2ba0644cb04b8d8b69d9d18511de39367edd214843dde753b74622e6f2b763"
NATIVE_STATE_FILE = "semantic_chandra_stage_schema_native.json"
NATIVE_STATE_SHA256 = "23979db219d946df3baa373f494ee9409ed786bcb8122c3f1b98b747fcbde581"
NATIVE_ADMISSION_FILE = "semantic_chandra_stage_schema_admission.sql"
NATIVE_ADMISSION_SHA256 = "d9953511ba8afe47110589e578309ce95c1c4bfa24fdb6f300617d29de952db4"


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
