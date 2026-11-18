"""Apply the frozen native candidate semantic_ddo_pe_n29."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n29"
down_revision = 'semantic_ddo_pe_n28'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n29_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "e19a9163b1ae7c7c0a68cfa95c0640ba65a527917b1a50409cf2923707b1d8bd"
NATIVE_STATE_FILE = "semantic_ddo_pe_n29_native.json"
NATIVE_STATE_SHA256 = "8246f8f112dee0e2b203e69909ee7110de6c1e3169f2819f6dd5b8c102991e97"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n29_admission.sql"
NATIVE_ADMISSION_SHA256 = "1f3da865ac04ac23707ac9d96fd35fd5c7d5618c4acfb2ab2fea55584247c7ba"


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
