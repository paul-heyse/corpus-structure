"""Add portable assessment history and explicit cross-source structural products; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_structure_20261105"
down_revision = "semantic_pce_batch_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_structure_20261105_native.json"
NATIVE_STATE_SHA256 = "bb85ee5e9fdccc343469067aa9da33a9a5bb2d4bc58232e74448b733c196a40a"
NATIVE_ADMISSION_FILE = "semantic_pce_structure_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "34175db79f70a9cdf2e56804edbcddc85023ff5c3d2d2022ce1796e1bf7dfc82"
NATIVE_UPGRADE_FILE = "semantic_pce_structure_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "16d2e757794ca843b09ea9caab4290759ad9e6622c33e595e20f68269a0fc861"


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
