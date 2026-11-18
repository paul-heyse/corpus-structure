"""Apply the frozen native candidate semantic_ddo_pe_n6."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n6"
down_revision = 'semantic_ddo_pe_n5'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n6_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "ab200969ac9ee99d1361af51f4b2fed4d41f57a607a4944e17d9e046428926c5"
NATIVE_STATE_FILE = "semantic_ddo_pe_n6_native.json"
NATIVE_STATE_SHA256 = "15a95fbb76d0bfcf7730320157258c64fc68716f04002d0c0303909533823e71"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n6_admission.sql"
NATIVE_ADMISSION_SHA256 = "181599c52c527b7c66813a720da8d1e1e90aeaf85a8aa883863505b51e9af655"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen native artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 2 or state["predecessor"] != down_revision:
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
