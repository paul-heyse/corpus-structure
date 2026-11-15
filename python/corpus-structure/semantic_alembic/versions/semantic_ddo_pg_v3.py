"""Apply the frozen native candidate semantic_ddo_pg_v3."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pg_v3"
down_revision = "semantic_ddo_pg_v2"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pg_v3_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "674974bfa1ed7e00d2ea48313365818d17f418a753a25bb9a31796f8eefd3b61"
NATIVE_STATE_FILE = "semantic_ddo_pg_v3_native.json"
NATIVE_STATE_SHA256 = "8136c3800f4910c733d4648afcd674af60fdf258f210f9206777e1bc56a776b0"
NATIVE_ADMISSION_FILE = "semantic_ddo_pg_v3_admission.sql"
NATIVE_ADMISSION_SHA256 = "2809bad98f0bc842d962d6174e3f053601f2492752f6aaf74d8e1fc67fb73285"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] not in {1, 2} or state["predecessor"] != down_revision:
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
