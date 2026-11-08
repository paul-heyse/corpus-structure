"""Apply the frozen native candidate semantic_nce_gs518_named_sets."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_nce_gs518_named_sets"
down_revision = "semantic_nce_audit_named_piece"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_nce_gs518_named_sets_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "65b484e4e9f5a532e7ecb5561d5ff154976e98eb37211dc0ac89ad73b2a5d460"
NATIVE_STATE_FILE = "semantic_nce_gs518_named_sets_native.json"
NATIVE_STATE_SHA256 = "b2e4539b55e33789098cc6db22d1ddd81f145b36cb2d58e3c639c970ce8a7ff0"
NATIVE_ADMISSION_FILE = "semantic_nce_gs518_named_sets_admission.sql"
NATIVE_ADMISSION_SHA256 = "68a5d97913605ef28e774775f849a35756635fac1e25b093cce56d43715d134f"


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
