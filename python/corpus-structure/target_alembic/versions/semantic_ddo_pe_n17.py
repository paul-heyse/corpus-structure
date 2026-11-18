"""Apply the frozen native candidate semantic_ddo_pe_n17."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n17"
down_revision = 'semantic_ddo_pe_n16'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n17_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "d5d047daf1566934412e99bfcd81b1713ddc8ef362bd225b72d68a0192bca9e9"
NATIVE_STATE_FILE = "semantic_ddo_pe_n17_native.json"
NATIVE_STATE_SHA256 = "10aa2142e28bec7bfe5ac5d5d4edfda8597d118650d6fd26c710758a0731fda1"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n17_admission.sql"
NATIVE_ADMISSION_SHA256 = "bbe5198a27e89ad56a3d0f95ff9622a7f27ed51bad7d10c779c74621bb72ac25"


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
