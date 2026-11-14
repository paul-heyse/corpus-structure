"""Apply the frozen native candidate semantic_test_pdf_recipe_guard."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_test_pdf_recipe_guard"
down_revision = "semantic_ddo_archive_v5"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_test_pdf_recipe_guard_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "315095712898a0344c572cd56c26dd22403f96d40a82365f294b6ebd178f4f1e"
NATIVE_STATE_FILE = "semantic_test_pdf_recipe_guard_native.json"
NATIVE_STATE_SHA256 = "7d16f1dd8e7efd5ac802b594cfa6e931ff1c7252919729e066fb7717a205f607"
NATIVE_ADMISSION_FILE = "semantic_test_pdf_recipe_guard_admission.sql"
NATIVE_ADMISSION_SHA256 = "c49a20fe1d63b5a4a920f6dd4e331b7daa113d7e63812e0558f8590d587d50c7"


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
