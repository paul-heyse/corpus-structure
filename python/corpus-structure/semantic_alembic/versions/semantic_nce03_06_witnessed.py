"""Apply the frozen native candidate semantic_nce03_06_witnessed."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce03_06_witnessed"
down_revision = "semantic_nce02_scope_guard"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce03_06_witnessed_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "108d221737fb04554dbf4711aa60e550d951325a5d549dca8037b72c351d4d63"
NATIVE_STATE_FILE = "semantic_nce03_06_witnessed_native.json"
NATIVE_STATE_SHA256 = "7a3e288c52898135212749cdfd8c7799f90cd050e56b870fa937247bf66a08d4"
NATIVE_ADMISSION_FILE = "semantic_nce03_06_witnessed_admission.sql"
NATIVE_ADMISSION_SHA256 = "182a1d7c27d90c56db720ea43ea155d9915ed180839fad087a46be56f37e8b84"


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
