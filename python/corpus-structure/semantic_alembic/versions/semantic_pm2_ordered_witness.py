"""Apply the frozen native candidate semantic_pm2_ordered_witness."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pm2_ordered_witness"
down_revision = "semantic_pm2_parser_payloads"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_pm2_ordered_witness_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "1d7e8bfbfb45383cb6db03f285f8fe76f692dc91aa899d07df90dfbda20e0331"
NATIVE_STATE_FILE = "semantic_pm2_ordered_witness_native.json"
NATIVE_STATE_SHA256 = "d8c401fcd2147a612085aae564f787d9b08951cf520503d06918d39bdba93666"
NATIVE_ADMISSION_FILE = "semantic_pm2_ordered_witness_admission.sql"
NATIVE_ADMISSION_SHA256 = "30866ec059e17bf48be8f7de7ad3ea2546f8f4377a56095298f6833c01c65ddb"


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
