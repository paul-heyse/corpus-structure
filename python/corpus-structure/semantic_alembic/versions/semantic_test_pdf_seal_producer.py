"""Apply the frozen native candidate semantic_test_pdf_seal_producer."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_test_pdf_seal_producer"
down_revision = "semantic_test_pdf_recipe_guard"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_test_pdf_seal_producer_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e0c084873ea3a8cd325731b1845eb0de41574bd5e8273d57f658d6490f76b90b"
NATIVE_STATE_FILE = "semantic_test_pdf_seal_producer_native.json"
NATIVE_STATE_SHA256 = "84df72a13145d2d0104b044f47c18754e484a7c57b7c2e2ba18db104ecc056c3"
NATIVE_ADMISSION_FILE = "semantic_test_pdf_seal_producer_admission.sql"
NATIVE_ADMISSION_SHA256 = "3199ac3fa7d430a7ab7df17bfa1660a4c95dd24cd2f149cafdcce7e29e2eeb7d"


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
