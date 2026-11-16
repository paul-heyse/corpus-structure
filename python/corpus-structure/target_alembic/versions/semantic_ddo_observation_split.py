"""Apply the frozen native candidate semantic_ddo_observation_split."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_observation_split"
down_revision = 'semantic_ddo_logical_family'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_observation_split_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "06da722062ef965944eb462de1299fb9960b8ec90a52eaa3fc3791690b8e210a"
NATIVE_STATE_FILE = "semantic_ddo_observation_split_native.json"
NATIVE_STATE_SHA256 = "5f0c8ee22239402054bb3f2b6d2497e94e4437f5f4522416498b8f2d32a3eaf3"
NATIVE_ADMISSION_FILE = "semantic_ddo_observation_split_admission.sql"
NATIVE_ADMISSION_SHA256 = "142e0cbec81f766941ebba4b2c4c09db6a24bd4c0d9299a79701234441536790"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 2 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))
    if state["version"] == 2:
        from corpus_structure.semantic.alembic_privileges import admit_privileges
        admit_privileges(op.get_bind(), state["privileges"])


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
