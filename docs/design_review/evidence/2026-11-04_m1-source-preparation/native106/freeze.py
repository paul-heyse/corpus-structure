"""Freeze a reviewed105→106 source-preparation transition; refuse existing destinations."""
import ast
import json
import re
import subprocess
from hashlib import sha256
from pathlib import Path

root = Path.cwd()
source = Path(__file__).parent / "candidate-003"
state_bytes = (source / "native_operations.json").read_bytes()
state = json.loads(state_bytes)
assert state["predecessor"] == "semantic_ac_attribute_20261103"
assert len(state["desired"]) == 133
assert {(item["after"] or item["before"])["identity"]["name"] for item in state["operations"]} == {
    "read_published_input_batch_rows", "read_published_relation_batch", "read_published_coverage_batch",
    "read_published_mapping_report_batch", "add_source_task_dependency", "execution_contract_descriptor",
}
module = ast.parse((source / "native_candidate.py").read_text())
insert = [node.args[0].value for node in ast.walk(module)
          if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
          and node.func.attr == "execute" and node.args and isinstance(node.args[0], ast.Constant)
          and isinstance(node.args[0].value, str) and node.args[0].value.startswith("INSERT INTO sem.physical_contract")]
assert len(insert) == 1
physical = (source / "physical.sql").read_text() + insert[0] + ";\n"
assert json.loads((source / "physical-owner.json").read_text())["owner"] == "corpus_sem_publisher"
admission = (source / "native_admission.sql").read_bytes()
stem = "semantic_m1_preparation_20261104"
versions = root / "python/corpus-structure/semantic_alembic/versions"
files = {
    stem + "_native.json": state_bytes,
    stem + "_admission.sql": admission,
    stem + "_physical.sql": physical.encode(),
}
code = f'''"""Owned linguistic products and same-view source dependencies; forward from frozen105."""
import json
from hashlib import sha256
from pathlib import Path
from alembic import op
from alembic.operations import Operations
from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import NativeObject, admit_native

revision = "{stem}"
down_revision = "semantic_ac_attribute_20261103"
branch_labels = None
depends_on = None
NATIVE_STATE_FILE = "{stem}_native.json"
NATIVE_STATE_SHA256 = "{sha256(state_bytes).hexdigest()}"
NATIVE_ADMISSION_FILE = "{stem}_admission.sql"
NATIVE_ADMISSION_SHA256 = "{sha256(admission).hexdigest()}"
PHYSICAL_STATE_FILE = "{stem}_physical.sql"
PHYSICAL_STATE_SHA256 = "{sha256(physical.encode()).hexdigest()}"

def _read(name, digest):
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("M1 preparation artifact differs: " + name)
    return content

def upgrade():
    state = json.loads(_read(NATIVE_STATE_FILE, NATIVE_STATE_SHA256))
    _read(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    physical = _read(PHYSICAL_STATE_FILE, PHYSICAL_STATE_SHA256).decode()
    if state["predecessor"] != down_revision or state["version"] != 1:
        raise RuntimeError("incompatible M1 preparation predecessor")
    original_role = op.get_bind().exec_driver_sql("SELECT current_user").scalar_one()
    op.execute("SET LOCAL ROLE corpus_sem_publisher")
    op.execute(physical)
    op.execute("SET LOCAL ROLE " + op.get_bind().dialect.identifier_preparer.quote(original_role))
    for transition in state["operations"]:
        Operations(op.get_context()).invoke(NativeTransitionOp.from_payload(transition))
    admit_native(op.get_bind(), tuple(NativeObject.from_payload(item) for item in state["desired"]))

def downgrade():
    raise RuntimeError("destructive M1 preparation downgrade refused; rebuild owned storage")
'''
code = subprocess.run(["uv", "run", "ruff", "format", "--isolated", "--line-length", "100", "-"],
                      input=code, text=True, capture_output=True, check=True).stdout
files["0106_m1_source_preparation.py"] = code.encode()
for name in files:
    if (versions / name).exists():
        raise FileExistsError("frozen destination already exists: " + name)
for name, value in files.items():
    (versions / name).write_bytes(value)
p = root / "python/corpus-structure/src/corpus_structure/semantic/execution_admission.py"
s = p.read_text()
for name, constant in [("execution_contract_descriptor", "_DESCRIPTOR_SHA256"),
                       ("require_execution_release", "_REQUIRE_SHA256")]:
    item = next(item for item in state["desired"] if item["identity"]["schema"] == "data" and item["identity"]["name"] == name)
    digest = sha256(item["catalog"]["body"].encode()).hexdigest()
    s = re.sub(rf'{constant} = "[a-f0-9]+"', f'{constant} = "{digest}"', s)
p.write_text(s)
print(json.dumps(dict(revision=stem, native_changes=len(state["operations"]), managed_objects=133, physical_check_changes=1)))
