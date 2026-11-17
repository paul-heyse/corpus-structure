"""Apply the frozen native candidate semantic_ddo_binding_reuse."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_binding_reuse"
down_revision = 'semantic_ddo_nullable_fields'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_binding_reuse_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "95af97646d4317346149a83ac5ba9161b97ecdba7edaa08f8b731740ffe8c7ae"
NATIVE_STATE_FILE = "semantic_ddo_binding_reuse_native.json"
NATIVE_STATE_SHA256 = "8c24722277cf5bf572d6e3643a495ce3d5b69bc53dffccff954f642bb8335789"
NATIVE_ADMISSION_FILE = "semantic_ddo_binding_reuse_admission.sql"
NATIVE_ADMISSION_SHA256 = "91ee0d4ee229853241a3b30e0adc49b9c1326204043df165ed4d466749f54004"


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
