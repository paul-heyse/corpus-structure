"""Apply the frozen native candidate semantic_ddo_sources_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_sources_v1"
down_revision = "semantic_ddo_acquire_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_sources_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "2d6b7c244f78d29200dc16e2a58fffeb91b5e5cf77b803d17c37e24e1d3c7007"
NATIVE_STATE_FILE = "semantic_ddo_sources_v1_native.json"
NATIVE_STATE_SHA256 = "8dc8ded7e710da5cf2db80581b807c2548eb53aa47212c52676a655b16d3250d"
NATIVE_ADMISSION_FILE = "semantic_ddo_sources_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "40ad7723eb198da19fd315849c40f0be2c04b8f64249a75fae703aa77462fa01"


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
