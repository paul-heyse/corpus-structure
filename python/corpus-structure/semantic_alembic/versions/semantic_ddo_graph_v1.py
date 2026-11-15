"""Apply the frozen native candidate semantic_ddo_graph_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_graph_v1"
down_revision = "semantic_ddo_source_v2"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_graph_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "03701b09c02642e1268c85d6d5239a422f33acacf1fb3bd399f684e8c263c8b2"
NATIVE_STATE_FILE = "semantic_ddo_graph_v1_native.json"
NATIVE_STATE_SHA256 = "24d40a238d85209ba1a9afdf02b028a4cd1e381eae7d37f431faeabae58f2be5"
NATIVE_ADMISSION_FILE = "semantic_ddo_graph_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "5fdd283e308fdab86c4428ab76406bd5d794ff8329c7f2e3070ea1aa87368c16"


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
