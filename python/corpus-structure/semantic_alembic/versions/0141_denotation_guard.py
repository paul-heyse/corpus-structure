"""Repair denotation guard precedence without changing semantic output; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_denotation_20261105"
down_revision = "semantic_pce_semantics_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_denotation_20261105_native.json"
NATIVE_STATE_SHA256 = "ab3890de7068721c729cd90820903c0122a3056aba82db9ec06701b3cf70655f"
NATIVE_ADMISSION_FILE = "semantic_pce_denotation_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "1623b36d4ccfbd1a0ac003d36347685aea7204848499441d893e6aa04bb43d91"
NATIVE_UPGRADE_FILE = "semantic_pce_denotation_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "3fc35e6c9ca3365c6ae4a535cd31823cfe7792fcbd263a7952356a3e849c8743"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen local publication artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible local publication predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive local publication downgrade refused")
