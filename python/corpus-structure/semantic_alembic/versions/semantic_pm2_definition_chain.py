"""Apply the frozen native candidate semantic_pm2_definition_chain."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_definition_chain"
down_revision = "semantic_pm2_ordered_witness"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_definition_chain_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d4dd07bc173addad6ea8681d37bbfe67b327a2512c56ac1a4142df5b018ec96c"
NATIVE_STATE_FILE = "semantic_pm2_definition_chain_native.json"
NATIVE_STATE_SHA256 = "14ff4cf7b5c338000fd527ffb4509ca1e763a95875a260bf81d6aed1715c8550"
NATIVE_ADMISSION_FILE = "semantic_pm2_definition_chain_admission.sql"
NATIVE_ADMISSION_SHA256 = "609bb5d15cc7780831d3d62726080fae515a0108035a8b6a348f9d3c9cb35142"


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
