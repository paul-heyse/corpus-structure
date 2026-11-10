"""Apply the frozen native candidate semantic_dmc_completion_repairs."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_dmc_completion_repairs"
down_revision = "semantic_dmc_digest_binding"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_dmc_completion_repairs_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "8da320c89608900e99308b6e414c27b46c8e718a8502c091b430bc5ca9748290"
NATIVE_STATE_FILE = "semantic_dmc_completion_repairs_native.json"
NATIVE_STATE_SHA256 = "7385da284ac447e8fe08408341b7abd3f977d1a0eb477e10d1144fa5da2df2e7"
NATIVE_ADMISSION_FILE = "semantic_dmc_completion_repairs_admission.sql"
NATIVE_ADMISSION_SHA256 = "b994a2e633f1e1dcc79b89ecc6401fb89dfb1e4de91fdc5d0519737239734a9e"


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
