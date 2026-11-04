"""Freeze final reading/context and bounded consumer execution bytes after native123."""

import json
import re
from hashlib import sha256
from pathlib import Path

source = Path(__file__).parent / "current-head-022"
state_bytes = (source / "native_operations.json").read_bytes()
state = json.loads(state_bytes)
assert state["predecessor"] == "semantic_m1_terminal_20261104"
assert len(state["operations"]) == 1 and len(state["desired"]) == 151
assert state["operations"][0]["after"]["identity"]["name"] == "execution_contract_descriptor"
admission = (source / "native_admission.sql").read_bytes()
versions = Path("python/corpus-structure/semantic_alembic/versions")
stem = "semantic_m1_readings_20261104"
code = (versions / "0123_m1_terminal_diagnostics.py").read_text()
code = code.replace("Retain final-run diagnostics without successful cut custody.",
                    "Admit retained reading contexts and bounded source support consumers.")
code = re.sub(r'revision = "[^"]+"', f'revision = "{stem}"', code, count=1)
code = re.sub(r'down_revision = "[^"]+"',
              'down_revision = "semantic_m1_terminal_20261104"', code, count=1)
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
    "0124_m1_reading_contexts.py": code.encode(),
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
print("frozen124: one reviewed execution descriptor successor;151 managed objects")
