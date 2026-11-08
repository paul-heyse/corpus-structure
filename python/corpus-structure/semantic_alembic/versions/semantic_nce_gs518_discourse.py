"""Apply the frozen native candidate semantic_nce_gs518_discourse."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_gs518_discourse"
down_revision = "semantic_nce_gs518_named_sets"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_gs518_discourse_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "9d598d0464edb98f7f99aeed9131a805fcf55f8b917f49da49efd3cddb6d4122"
NATIVE_STATE_FILE = "semantic_nce_gs518_discourse_native.json"
NATIVE_STATE_SHA256 = "fb334c77cd1c1ac24e8b34e29a4190709d6871a87150a456977504ad373e9ed3"
NATIVE_ADMISSION_FILE = "semantic_nce_gs518_discourse_admission.sql"
NATIVE_ADMISSION_SHA256 = "046a7d60e86853a3f38445f27aac0f015c482812187130fba8cef5284c14ae3d"


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
