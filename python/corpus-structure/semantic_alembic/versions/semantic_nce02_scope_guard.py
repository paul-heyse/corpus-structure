"""Apply the frozen native candidate semantic_nce02_scope_guard."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce02_scope_guard"
down_revision = "semantic_nce02_qualifier_scope"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce02_scope_guard_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "4f147cecb2cb6ec96d67d8c06495e93e172e64bfea61bef7f75cbf7628ff932f"
NATIVE_STATE_FILE = "semantic_nce02_scope_guard_native.json"
NATIVE_STATE_SHA256 = "2bfee9c67e9fb23b52870f562f773fc8223197a5d731c5b3e3ebe9067555e8c9"
NATIVE_ADMISSION_FILE = "semantic_nce02_scope_guard_admission.sql"
NATIVE_ADMISSION_SHA256 = "ef3db74fae82dc68b0173f7a73eb56bb43413a2e3b201effa092d77efc7c7816"


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
