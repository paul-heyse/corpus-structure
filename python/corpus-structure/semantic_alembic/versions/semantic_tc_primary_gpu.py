"""Apply the frozen native candidate semantic_tc_primary_gpu."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc_primary_gpu"
down_revision = "semantic_bep_inventory"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc_primary_gpu_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "2ff9184b8404efcb12cf38068f80c75f0cc4caa9023ab7e3c0d45c58047bd201"
NATIVE_STATE_FILE = "semantic_tc_primary_gpu_native.json"
NATIVE_STATE_SHA256 = "8a180f985e304e466c7ef691897070feddffccbf4e1635722cd7c0457a53c954"
NATIVE_ADMISSION_FILE = "semantic_tc_primary_gpu_admission.sql"
NATIVE_ADMISSION_SHA256 = "a753446ed3a9b6445c3eaf8cc2d473e30accb66e7448bb0fac79f150be4f7590"


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
