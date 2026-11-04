"""Adopt the registered native retained-source replay guard without changing release meaning."""

import json
import re
from hashlib import sha256
from pathlib import Path

source = Path(__file__).parent / "current-head-025"
state_bytes = (source / "native_operations.json").read_bytes()
state = json.loads(state_bytes)
assert state["predecessor"] == "semantic_m1_readings_20261104"
assert len(state["desired"]) == 152 and len(state["operations"]) == 2
assert {row["after"]["identity"]["name"] for row in state["operations"]} == {
    "select_reused_source_views", "execution_contract_descriptor"
}
admission = (source / "native_admission.sql").read_bytes()
versions = Path("python/corpus-structure/semantic_alembic/versions")
stem = "semantic_m1_reuse_20261104"
code = (versions / "0124_m1_reading_contexts.py").read_text()
code = code.replace("Admit retained reading contexts and bounded source support consumers.",
                    "Replay exact retained source-product selections after task reuse.")
code = re.sub(r'revision = "[^"]+"', f'revision = "{stem}"', code, count=1)
code = re.sub(r'down_revision = "[^"]+"',
              'down_revision = "semantic_m1_readings_20261104"', code, count=1)
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
    "0125_m1_retained_source_reuse.py": code.encode(),
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
print("frozen125: retained-source guard + native descriptor;152 managed objects")
