"""Apply the frozen native candidate semantic_chandra_grouped."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_chandra_grouped"
down_revision = "semantic_chandra_enrichment_v2"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_chandra_grouped_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e8a25fab1e622ecc4d8798710c116856bc61b9d30063e0b696a7d416b8345960"
NATIVE_STATE_FILE = "semantic_chandra_grouped_native.json"
NATIVE_STATE_SHA256 = "e0987ba902cd39d0eaa9446cf464bc17a00ee64190f3cab6955b3f16b7677d1d"
NATIVE_ADMISSION_FILE = "semantic_chandra_grouped_admission.sql"
NATIVE_ADMISSION_SHA256 = "e0953444bae267ee16e150f4783500cf20d724c940be74c74931e495b3780953"


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
