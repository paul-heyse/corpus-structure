"""Authorize explicitly selected already-exposed feature-fit review without partition relabeling."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_exposure_20261105"
down_revision = "semantic_pce_structure_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_exposure_20261105_native.json"
NATIVE_STATE_SHA256 = "599fc7e1d1a4e523e0431193c4f573d6cac1456c35f1a5cdf94e73713ef056f8"
NATIVE_ADMISSION_FILE = "semantic_pce_exposure_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "aae75a5a95506a3b3c56a51958a06d3e01913341587d2ac73bd14dfde8069cdb"
NATIVE_UPGRADE_FILE = "semantic_pce_exposure_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "465d7054e34f9c59d753863ee0ca383b749cdcbb1c6b6b1560b8bc7d0ba2ff09"


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
