"""Apply the frozen native candidate semantic_ddo_pe_n11."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n11"
down_revision = 'semantic_ddo_pe_n10'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n11_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "142a22c9277121867e3cac218cec49058862b19079866979fef07e2ac09402ca"
NATIVE_STATE_FILE = "semantic_ddo_pe_n11_native.json"
NATIVE_STATE_SHA256 = "a0670d4e5054aec18147c694fa77df4e15b688e5ea8df2360619261f0e18fb88"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n11_admission.sql"
NATIVE_ADMISSION_SHA256 = "dc65f0ddd4e557de1a199ac26eaabceee16c949796f0728b9bb1ddd869f1eb4e"


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
