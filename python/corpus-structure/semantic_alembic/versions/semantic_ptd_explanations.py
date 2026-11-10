"""Apply the frozen native candidate semantic_ptd_explanations."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ptd_explanations"
down_revision = "semantic_ptd_runtime_compiler"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ptd_explanations_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "66b909216fddb4bf059f3a0168302e6381f98924bea6f8fcd4ed471181f26990"
NATIVE_STATE_FILE = "semantic_ptd_explanations_native.json"
NATIVE_STATE_SHA256 = "a0ea1a321cdba2daf189c8d5a41cf2f59b4ae6fe0b6f6f4664476f8e768e87bd"
NATIVE_ADMISSION_FILE = "semantic_ptd_explanations_admission.sql"
NATIVE_ADMISSION_SHA256 = "4506d31cf2708fcfdf06a42ebd548c43b409d3691f78398775fb3fbe8e3c1115"


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
