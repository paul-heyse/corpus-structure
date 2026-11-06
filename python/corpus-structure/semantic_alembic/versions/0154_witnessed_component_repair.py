"""Retain witnessed components and frozen source-opportunity frames; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_repair_20261106"
down_revision = "semantic_wce_components_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_component_repair_20261106_native.json"
NATIVE_STATE_SHA256 = "3b5a3dca98e35f32954cfec631d3425f720de5378992dfb42148641a18caf3c7"
NATIVE_ADMISSION_FILE = "semantic_wce_component_repair_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "27100ef6596e552f54d036357860b21d8296f5596a1be77c6451c2c69c253f02"
NATIVE_UPGRADE_FILE = "semantic_wce_component_repair_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "1aa1f9aff4924cba004e2d2b41bade955c2b0b2a1c6296326a80be72a722ab69"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen WCE artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible WCE predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive WCE downgrade refused")
