"""Apply the frozen native candidate semantic_ddo_archive_v1."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_ddo_archive_v1"
down_revision = "semantic_ddo_original_v1"
branch_labels = None
depends_on = None
NATIVE_UPGRADE_FILE = "semantic_ddo_archive_v1_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "a91cbebf2c0ad8a537ba2ced11aab5aa262e7c9883b48d06010d92af1b65d09d"
NATIVE_STATE_FILE = "semantic_ddo_archive_v1_native.json"
NATIVE_STATE_SHA256 = "ae429f24b883072c6c28ed00892baebc8b6de69784b991c3d851dfce129fef8d"
NATIVE_ADMISSION_FILE = "semantic_ddo_archive_v1_admission.sql"
NATIVE_ADMISSION_SHA256 = "a1af8534b526c3d0cdf21d0030ba05b195106ed4561c1990d1ec253f66a31abf"


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
