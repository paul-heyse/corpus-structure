"""Apply the frozen native candidate semantic_dmc_interpretations."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_dmc_interpretations"
down_revision = "semantic_dmc_terminology"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_dmc_interpretations_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "9bd1bd437b10d40b7eaf1a7bf8fae91a3e7d9eff426291b80bda4eab18814ea0"
NATIVE_STATE_FILE = "semantic_dmc_interpretations_native.json"
NATIVE_STATE_SHA256 = "46c5e81e1d69f60d36083f97bb3cc3e5d583fb954a31f129a2ae75341d1b69ac"
NATIVE_ADMISSION_FILE = "semantic_dmc_interpretations_admission.sql"
NATIVE_ADMISSION_SHA256 = "6ca48221f5ce225be29b75ed5d64049b6c0e351dd35c6a597492103431984b84"


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
