"""Install the current witnessed component, relationship and applicability design."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_target_20261106"
down_revision = "semantic_wce_roles_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_target_20261106_native.json"
NATIVE_STATE_SHA256 = "3f1f47f0c7444ea38b940effe9ad4a493cd55aae4c6310f59340474f05969eaf"
NATIVE_ADMISSION_FILE = "semantic_wce_target_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "e9346bc5aa27cc38529f0f67f95d7d402bc04f7629f996b356024e264f2c8f12"
NATIVE_UPGRADE_FILE = "semantic_wce_target_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "070c2a5a9ca2ed2f51216824f1280c3fa26dc59e9e4c94f213ea4df8c5f49d90"


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
