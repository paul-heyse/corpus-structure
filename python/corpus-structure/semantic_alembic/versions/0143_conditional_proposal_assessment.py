"""Assess conditional proposal ports without relabelling them as relations; forward only."""
import json
from hashlib import sha256
from pathlib import Path

from alembic import op

from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "semantic_pce_ports_20261105"
down_revision = "semantic_pce_partition_20261105"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "semantic_pce_ports_20261105_native.json"
NATIVE_STATE_SHA256 = "c22ea312c07fc13bea7cc7e03b7c89f97f63dec1fcc42324a16749f7a4eb506f"
NATIVE_ADMISSION_FILE = "semantic_pce_ports_20261105_admission.sql"
NATIVE_ADMISSION_SHA256 = "83241c01e851acbb6326ced9f391ad52c3ec35402d32aa2413070541ba7eb798"
NATIVE_UPGRADE_FILE = "semantic_pce_ports_20261105_upgrade.txt"
NATIVE_UPGRADE_SHA256 = "5468d39521544a5790eed95bc53943189ebdb91c1d632dc8cecde6fe17155ff5"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen local publication artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible local publication predecessor")
    source = _read(NATIVE_UPGRADE_FILE, NATIVE_UPGRADE_SHA256)
    namespace = {}
    exec(compile(source, NATIVE_UPGRADE_FILE, "exec"), namespace)
    namespace["upgrade"]()
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive local publication downgrade refused")
