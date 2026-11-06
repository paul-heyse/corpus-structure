"""Install current source coverage, structural composition, dossier and operation fitting."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_composed_20261106"
down_revision = "semantic_wce_baseline_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_composed_20261106_native.json"
NATIVE_STATE_SHA256 = "1c27e7504f67d93c0361db69a7f78cb417f7d5f0d49dc3cd60991d1b7267446b"
NATIVE_ADMISSION_FILE = "semantic_wce_composed_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "f2e1d0566142af51e4c65f499412ce197a78d1f29c54bab4d88e074d6850849b"
NATIVE_UPGRADE_FILE = "semantic_wce_composed_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "7c84072b22fbe919184cf664046ed3462aa97bae0358cf456b89d788c2f99e94"


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
