"""Apply the frozen native candidate semantic_ddo_source_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_source_v1"
down_revision = "semantic_ddo_pg_v3"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_source_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "f5465d5a184b1fa6bc83b0a3d1a8e4e97921fbcc8b95776eba15efff3ef9fa27"
NATIVE_STATE_FILE = "semantic_ddo_source_v1_native.json"
NATIVE_STATE_SHA256 = "e780c9de412b5735f5e56759785e3295c41ea8d6295e0a675d495d27e73a5b65"
NATIVE_ADMISSION_FILE = "semantic_ddo_source_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "6f62040ad1b2d10e2f2410f47223e08aa700b8fd79b6d821bcccc182535c00e7"


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
