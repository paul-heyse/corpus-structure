"""Apply the frozen native candidate semantic_tc03_09_carriers."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc03_09_carriers"
down_revision = "semantic_tc03_09_projection"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc03_09_carriers_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "20f22159447cc8ef5130bcb0dbf3cd1131b8822fcae1e1feae88e1d67fdcdb91"
NATIVE_STATE_FILE = "semantic_tc03_09_carriers_native.json"
NATIVE_STATE_SHA256 = "f3035841c02e455b8916340f9aa471e0f0d1858af576611aeee14450f9b02c2d"
NATIVE_ADMISSION_FILE = "semantic_tc03_09_carriers_admission.sql"
NATIVE_ADMISSION_SHA256 = "6197b856d69f5f7347f8f219e126eab07ae28886f8d15f35de0b5386a8085d39"


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
