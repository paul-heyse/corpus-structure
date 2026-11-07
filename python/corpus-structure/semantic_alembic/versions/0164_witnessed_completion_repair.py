"""Install witnessed comparison, rooted dossiers and source-conditioned pilot guards."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_wce_gaps_20261106"
down_revision = "semantic_wce_batch_20261106"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_wce_gaps_20261106_native.json"
NATIVE_STATE_SHA256 = "9e469eb38d1e2a58fa30f3e197d3510fc405f72bebc0c94d83c6d5cf68b7ef07"
NATIVE_ADMISSION_FILE = "semantic_wce_gaps_20261106_admission.sql"
NATIVE_ADMISSION_SHA256 = "72b5959301d43420f3adaf75321a789a0ee8d405d1a529e0865991360996e095"
NATIVE_UPGRADE_FILE = "semantic_wce_gaps_20261106_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "307be1b1ef628aeda5e2213d433599f99d5b4b011ea4d5b55f6ec14341eab51f"


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
