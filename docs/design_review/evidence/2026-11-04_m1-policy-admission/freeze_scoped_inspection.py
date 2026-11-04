"""Freeze explicit compatible-reference native ownership after rollback authoring."""
import json
import re
from hashlib import sha256
from pathlib import Path

source = Path(__file__).parent / "current-head-033"
state_bytes = (source / "native_operations.json").read_bytes()
state = json.loads(state_bytes)
assert state["predecessor"] == "semantic_m1_ref_scope_20261104"
assert len(state["desired"]) == 160 and len(state["operations"]) == 1
assert {(row.get("after") or row.get("before"))["identity"]["name"] for row in state["operations"]} == {"execution_contract_descriptor"}
assert all((row.get("after") or row.get("before"))["identity"]["kind"] == "function" for row in state["operations"])
admission = (source / "native_admission.sql").read_bytes()
versions = Path("python/corpus-structure/semantic_alembic/versions")
stem = "semantic_m1_inspect_20261104"
code = (versions / "0127_m1_reference_scope.py").read_text()
code = code.replace("Disambiguate frozen-reference gap and fitting frame SQL scopes.",
                    "Admit scoped native inspection with complete retained inventory validation.")
code = code.replace("M1 score", "M1 reference")
code = re.sub(r'revision = "[^"]+"', f'revision = "{stem}"', code, count=1)
code = re.sub(r'down_revision = "[^"]+"', 'down_revision = "semantic_m1_ref_scope_20261104"', code, count=1)
for name, value in {
    "NATIVE_STATE_FILE": stem + "_native.json",
    "NATIVE_STATE_SHA256": sha256(state_bytes).hexdigest(),
    "NATIVE_ADMISSION_FILE": stem + "_admission.sql",
    "NATIVE_ADMISSION_SHA256": sha256(admission).hexdigest(),
}.items():
    code = re.sub(rf'{name} = "[^"]+"', f'{name} = "{value}"', code)
for name, content in {
    stem + "_native.json": state_bytes,
    stem + "_admission.sql": admission,
    "0128_m1_scoped_inspection.py": code.encode(),
}.items():
    with (versions / name).open("xb") as output:
        output.write(content)
path = Path("python/corpus-structure/src/corpus_structure/semantic/execution_admission.py")
content = path.read_text()
for name, constant in (("execution_contract_descriptor", "_DESCRIPTOR_SHA256"),
                       ("require_execution_release", "_REQUIRE_SHA256")):
    item = next(item for item in state["desired"]
                if item["identity"]["schema"] == "data" and item["identity"]["name"] == name)
    digest = sha256(item["catalog"]["body"].encode()).hexdigest()
    content = re.sub(rf'{constant} = "[a-f0-9]+"', f'{constant} = "{digest}"', content)
path.write_text(content)
print("frozen128: scoped inspection admission,160 managed objects,1 native function")
