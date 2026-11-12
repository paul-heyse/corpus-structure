"""Apply the frozen native candidate semantic_tc_choice_assessment."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_tc_choice_assessment"
down_revision = "semantic_tc_primary_gpu"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_tc_choice_assessment_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "339286a060b3ef550b19f675e160b203a9bd1ef55f38120e40e93f1294f9862c"
NATIVE_STATE_FILE = "semantic_tc_choice_assessment_native.json"
NATIVE_STATE_SHA256 = "f5340db385cd39e54dc535a0cb45a5286acede16de5c4f990139bfca87406314"
NATIVE_ADMISSION_FILE = "semantic_tc_choice_assessment_admission.sql"
NATIVE_ADMISSION_SHA256 = "ff0ea9dcd991482c9ed874b817ca16d8ec05b14791de87257c12792ec2a99e89"


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
