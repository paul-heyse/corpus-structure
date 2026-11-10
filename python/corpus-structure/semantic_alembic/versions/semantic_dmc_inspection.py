"""Apply the frozen native candidate semantic_dmc_inspection."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_dmc_inspection"
down_revision = "semantic_ptd_completion_repairs"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_dmc_inspection_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "b1950984239879f56238028753fe04a4b35a90ab822e5b706fe5aa1822fabb40"
NATIVE_STATE_FILE = "semantic_dmc_inspection_native.json"
NATIVE_STATE_SHA256 = "058f035cc02ca38d3f5e6da73ef87f4c9b839bafe7d53db5c7dd9b1d53ac10a7"
NATIVE_ADMISSION_FILE = "semantic_dmc_inspection_admission.sql"
NATIVE_ADMISSION_SHA256 = "c4b7fe0993b373de9d8e81b48ed3d8dcc5ea73af0413a4b9bbba840c8e807164"


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
