"""Apply the frozen native candidate semantic_dmc_digest_binding."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_dmc_digest_binding"
down_revision = "semantic_dmc_unit_references"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_dmc_digest_binding_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "5e64be4cffb41bdbe607fd1a3d4c6756bcca82840656181137df2df4a532271a"
NATIVE_STATE_FILE = "semantic_dmc_digest_binding_native.json"
NATIVE_STATE_SHA256 = "10539864f86b864ace38396d9c0e0750e0c506014a7a01c47dd878ef7903bfd7"
NATIVE_ADMISSION_FILE = "semantic_dmc_digest_binding_admission.sql"
NATIVE_ADMISSION_SHA256 = "6ca48221f5ce225be29b75ed5d64049b6c0e351dd35c6a597492103431984b84"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible native predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
