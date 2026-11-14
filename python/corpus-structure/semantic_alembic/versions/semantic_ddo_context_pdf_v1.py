"""Apply the frozen native candidate semantic_ddo_context_pdf_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_context_pdf_v1"
down_revision = "semantic_ddo_bound_rows_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_context_pdf_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "16042976b4e258c78880a31dfd70139aa89f3f8a51b6e345d866d481d2fd1611"
NATIVE_STATE_FILE = "semantic_ddo_context_pdf_v1_native.json"
NATIVE_STATE_SHA256 = "c45606eb59b64feebcedaf141f3663b083e93eda277d038f61419303f20448fa"
NATIVE_ADMISSION_FILE = "semantic_ddo_context_pdf_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "5902970f5ae7f544ba3ee9dcf4c1c122f4bc58132aad6b7b3b38a8fbe325ecb0"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] not in {1, 2} or state["predecessor"] != down_revision:
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
