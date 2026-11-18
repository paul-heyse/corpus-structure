"""Apply the frozen native candidate semantic_ddo_pe_n20."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_pe_n20"
down_revision = 'semantic_ddo_pe_n19'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_pe_n20_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "89b5563e65e7233fe5a2bf645b77196e3e8827f81eb55a87ef0b7101cdeb54e9"
NATIVE_STATE_FILE = "semantic_ddo_pe_n20_native.json"
NATIVE_STATE_SHA256 = "4fbb984a1bfc60e0555786c23ad5bfa4ce7fd24b2d0ab9965122947ce63bfd8b"
NATIVE_ADMISSION_FILE = "semantic_ddo_pe_n20_admission.sql"
NATIVE_ADMISSION_SHA256 = "abdab04373646ef9c250cadb06843c6821438961542d9c76492e9ae9d63bf3c1"


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
