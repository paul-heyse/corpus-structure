"""Apply the frozen native candidate semantic_chandra_enrichment_v2."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_chandra_enrichment_v2"
down_revision = "semantic_chandra_input_custody"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_chandra_enrichment_v2_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "a3e08ecd38f24f36e2abf236f7a2cdad93b74546e40d472b7cd83b20c197cedb"
NATIVE_STATE_FILE = "semantic_chandra_enrichment_v2_native.json"
NATIVE_STATE_SHA256 = "c3aeccb8309ae44c156a96770256490544e92397d353647a614febd34b81c3d3"
NATIVE_ADMISSION_FILE = "semantic_chandra_enrichment_v2_admission.sql"
NATIVE_ADMISSION_SHA256 = "caa2cf24c8452f9071387e432d45fce650f7056e2fd7eabbfbb2241f7841f113"


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
