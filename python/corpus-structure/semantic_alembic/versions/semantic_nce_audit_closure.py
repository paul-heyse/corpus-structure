"""Apply the frozen native candidate semantic_nce_audit_closure."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_audit_closure"
down_revision = "semantic_nce07_12_replay"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_audit_closure_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "dbc884677594cc1a2c182514f547dcde80bd46d41c81184435c3b0dd9e99bf66"
NATIVE_STATE_FILE = "semantic_nce_audit_closure_native.json"
NATIVE_STATE_SHA256 = "1776a152ae15e6f2e57ccb720a6e5580e0002c31bbdcfab1e24a787ef46dee73"
NATIVE_ADMISSION_FILE = "semantic_nce_audit_closure_admission.sql"
NATIVE_ADMISSION_SHA256 = "3192ac6c8bd22caba99ff8b2b0f77dca27954d22394e0308b87a48d752b55ff8"


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
