"""Apply the frozen native candidate semantic_sbx_qualified_reads."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_sbx_qualified_reads"
down_revision = 'semantic_sbx_answer_guards'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_sbx_qualified_reads_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "ab44a7aaeae0a23bd45799c6f1043cc0678e8144149b08d435d9b1103743dd9d"
NATIVE_STATE_FILE = "semantic_sbx_qualified_reads_native.json"
NATIVE_STATE_SHA256 = "a684ae1d0f90bbe6b0726bfdcaacd704d21683dfe5344c628fcc0e735f6ea95c"
NATIVE_ADMISSION_FILE = "semantic_sbx_qualified_reads_admission.sql"
NATIVE_ADMISSION_SHA256 = "c713cf5d448c3872d8cfd7b66c36ef0bfc642bfd79f50d8a85e05d2f420c4f58"


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
        admit_privileges(
            op.get_bind(), state["privileges"],
            purpose_roles=state.get("privilege_purpose_roles"),
        )


def downgrade():
    raise RuntimeError("native candidate downgrade is unsupported")
