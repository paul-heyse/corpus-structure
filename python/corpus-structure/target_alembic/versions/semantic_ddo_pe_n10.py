"""Apply the frozen native candidate semantic_ddo_pe_n10."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n10"
down_revision = 'semantic_ddo_pe_n9'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n10_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "fe1df51effdac558b64ea8df98e75679d43b9dc84176bd42946eecc243e2ec97"
NATIVE_STATE_FILE = "semantic_ddo_pe_n10_native.json"
NATIVE_STATE_SHA256 = "274eda1ae1cfde01a2cf0709e5fe181f1398415f14a98225b1781cb58bcca6f5"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n10_admission.sql"
NATIVE_ADMISSION_SHA256 = "e598d43a77e6b4c45906f2bd90ea142dc00fbfbb21d873599f036a450fa80be5"


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
