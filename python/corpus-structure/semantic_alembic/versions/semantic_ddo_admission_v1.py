"""Apply the frozen native candidate semantic_ddo_admission_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_admission_v1"
down_revision = "semantic_ddo_inputs_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_admission_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "bff0a15020a3bec70d485bcef6ec2145d157f611dd1c1e5a4ea56e6c33d32cae"
NATIVE_STATE_FILE = "semantic_ddo_admission_v1_native.json"
NATIVE_STATE_SHA256 = "e6c35763ebaf320dfa51a90450ede3237d5fbc7186f4140b6e79425dbd731cda"
NATIVE_ADMISSION_FILE = "semantic_ddo_admission_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "39f68b2ce47853ed82d2d592e5dd138909c08ef7ed80b9dab8cd7340d26eda7f"


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
