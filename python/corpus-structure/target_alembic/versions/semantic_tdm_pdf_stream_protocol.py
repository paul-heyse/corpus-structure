"""Apply the frozen native candidate semantic_tdm_pdf_stream_protocol."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tdm_pdf_stream_protocol"
down_revision = 'semantic_ddo_pe_n13'
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tdm_pdf_stream_protocol_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "6690ba1e8c585bf77cb3ac0353b80ff6bdfa3980d47d1e7980669bec7ac7ca55"
NATIVE_STATE_FILE = "semantic_tdm_pdf_stream_protocol_native.json"
NATIVE_STATE_SHA256 = "cad9f7510210f9b537a29342ad24c9bf9b972046c349b1a2b4b64fab03e8fb34"
NATIVE_ADMISSION_FILE = "semantic_tdm_pdf_stream_protocol_admission.sql"
NATIVE_ADMISSION_SHA256 = "eda7944620f5f55bc990bd0bfd90f9e573764caaad49ee68256edd0dd9a48d31"


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
