"""Materialize only the reviewed native-only successor of frozen103."""

import json
import re
import sys
from hashlib import sha256
from pathlib import Path

root = Path.cwd()
source = Path(__file__).with_name(sys.argv[1] if len(sys.argv) > 1 else "candidate-104-001")
state_bytes = (source / "native_operations.json").read_bytes()
admission = (source / "native_admission.sql").read_bytes()
state = json.loads(state_bytes)
assert state["predecessor"] == "semantic_ac_lineage_20261103"
assert {row["after"]["identity"]["name"] for row in state["operations"]} == {
    "validate_pre_inference_state", "execution_contract_descriptor"
}
versions = root / "python/corpus-structure/semantic_alembic/versions"
stem = "semantic_ac_import_20261103"
code = f'''"""Imported declaration-only membership with exact prior lineage; forward from frozen103."""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "{stem}"
down_revision = "semantic_ac_lineage_20261103"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "{stem}_native.json"
NATIVE_STATE_SHA256 = "{sha256(state_bytes).hexdigest()}"
NATIVE_ADMISSION_FILE = "{stem}_admission.sql"
NATIVE_ADMISSION_SHA256 = "{sha256(admission).hexdigest()}"


def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("native import artifact differs: " + name)
    return content


def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible native import predecessor")
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))


def downgrade():
    raise RuntimeError("destructive import downgrade refused; rebuild an owned database")
'''
# Format the prospective wrapper before writing the frozen artifact path.
import subprocess

formatted = subprocess.run(
    ["uv", "run", "ruff", "format", "--isolated", "--line-length", "100", "-"],
    input=code, text=True, capture_output=True, check=True,
).stdout
(versions / "0104_imported_declaration_membership.py").write_text(formatted)
(versions / f"{stem}_native.json").write_bytes(state_bytes)
(versions / f"{stem}_admission.sql").write_bytes(admission)
p = root / "python/corpus-structure/src/corpus_structure/semantic/execution_admission.py"
text = p.read_text()
for name, constant in [("execution_contract_descriptor", "_DESCRIPTOR_SHA256"),
                       ("require_execution_release", "_REQUIRE_SHA256")]:
    item = next(x for x in state["desired"] if x["identity"]["schema"] == "data"
                and x["identity"]["name"] == name)
    digest = sha256(item["catalog"]["body"].encode()).hexdigest()
    text = re.sub(rf'{constant} = "[a-f0-9]+"', f'{constant} = "{digest}"', text)
p.write_text(text)
print({"revision": stem, "native_operations": len(state["operations"]), "physical_changes": 0})
