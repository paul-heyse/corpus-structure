"""Apply the frozen native candidate semantic_tc03_09_finalize."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc03_09_finalize"
down_revision = "semantic_tc03_09_guards"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc03_09_finalize_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "340d1955d5116dcbf9178d7914defe7e54b2aec216c4abb678978a11a8dfd000"
NATIVE_STATE_FILE = "semantic_tc03_09_finalize_native.json"
NATIVE_STATE_SHA256 = "ed0ebe01f86c566c60f2362767b828122c484729d8a283e4aa31ecc1e0786765"
NATIVE_ADMISSION_FILE = "semantic_tc03_09_finalize_admission.sql"
NATIVE_ADMISSION_SHA256 = "d98aaac601b6cf81c9920b1dc0425713df02f994c0573a24d8b526797a8e8ec6"


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
