"""Apply the frozen native candidate semantic_ddo_support_reference."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_support_reference"
down_revision = 'semantic_ddo_stable_read_renewal'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_support_reference_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "c0561021d247f93f3bcf97efe07917cc8e260920139665d32c66a40ca3cd5d7d"
NATIVE_STATE_FILE = "semantic_ddo_support_reference_native.json"
NATIVE_STATE_SHA256 = "027f8bbbc79f64708d6285e2684c1be64147d846a5613fb76da8b351c69c8d4f"
NATIVE_ADMISSION_FILE = "semantic_ddo_support_reference_admission.sql"
NATIVE_ADMISSION_SHA256 = "cae8e382d651766edd910c81c2b625013abe3a87e5920b36fd606d1f117f98c2"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 2 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))
    if state["version"] == 2:
        from corpus_structure.semantic.alembic_privileges import admit_privileges
        admit_privileges(op.get_bind(), state["privileges"])


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
