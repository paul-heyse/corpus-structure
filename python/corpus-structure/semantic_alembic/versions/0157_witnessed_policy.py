"""Deploy witnessed helper closure and defining-occurrence policy enforcement."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_policy_20261106"
down_revision = "semantic_wce_meanings_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_policy_20261106_native.json"
NATIVE_STATE_SHA256 = "c9e326007027456750299ce4d33c6997bf36f12eff78768522b69ebc37cd6de0"
NATIVE_ADMISSION_FILE = "semantic_wce_policy_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "49caf69598185d869ee9e04f9cf55dfd246b27cf4ffaea643351bb9a99a64614"
NATIVE_UPGRADE_FILE = "semantic_wce_policy_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "ec1b63803970302b0525e27748bba4785105b5ecb47bc11c3ce47f06e529cde1"


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
