"""Apply the frozen native candidate semantic_dma_00_04."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_dma_00_04"
down_revision = "semantic_chandra_pdf_ancestry"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_dma_00_04_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "fb2d1494a4efc4d50650530ef50f308a44dc31a5ca0c89ea7f015c5ff3893352"
NATIVE_STATE_FILE = "semantic_dma_00_04_native.json"
NATIVE_STATE_SHA256 = "54a880155d33281dcf40ae90adc12e26ea0cd9f0e725fd6dc059d79894803be4"
NATIVE_ADMISSION_FILE = "semantic_dma_00_04_admission.sql"
NATIVE_ADMISSION_SHA256 = "5cbf2b5127d03e444944511057a41182ad12ac3864fefa0a3fe343ce50d2b8c5"


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
