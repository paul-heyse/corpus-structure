"""Freeze reviewed retained native selection provenance without changing predecessors."""

import json
import re
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.native_products import current_authoring_provenance

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
SOURCE = HERE / "raw/author-001"
VERSIONS = ROOT / "python/corpus-structure/semantic_alembic/versions"
REVISION = "semantic_um_selector_20261103"
PREDECESSOR = "semantic_um_stdio_20261102"

report = json.loads((SOURCE / "result.json").read_bytes())
assert report["outcome"] == "passed"
assert report["native_operations"] == 1 and report["ordinary_operations"] == 0
assert report["descriptor_changed"] == ["inputs", "model_id"]
assert report["changed_inputs"] == [
    "execution/implementation/invocation/operations.py",
    "execution/implementation/pdf/recognition_methods.py",
]
assert current_authoring_provenance().model_id == report["current_model_id"]
state = json.loads((SOURCE / "native.json").read_bytes())
assert state["predecessor"] == PREDECESSOR and len(state["operations"]) == 1
pins = {
    item["identity"]["name"]: sha256(item["catalog"]["body"].encode()).hexdigest()
    for item in state["desired"]
    if item["identity"]["name"]
    in {"execution_contract_descriptor", "require_execution_release"}
}
artifacts = {}
for suffix in ("native.json", "admission.sql"):
    content = (SOURCE / suffix).read_bytes()
    target = VERSIONS / (REVISION + "_" + suffix)
    if target.exists():
        assert target.read_bytes() == content
    else:
        target.write_bytes(content)
    artifacts[suffix] = {"name": target.name, "sha256": sha256(content).hexdigest()}

wrapper = (VERSIONS / "0097_um_worker_stdio.py").read_text()
wrapper = (
    '"""Frozen retained native selection source provenance.\n\n'
    "Only the execution descriptor's model/input provenance changes.\n"
    'Physical metadata, privileges and native guard policy remain unchanged.\n"""\n\n'
    + wrapper[wrapper.index("import json") :]
)
wrapper = wrapper.replace(
    'revision = "semantic_um_stdio_20261102"', f'revision = "{REVISION}"'
).replace(
    'down_revision = "semantic_um_closure_20261102"',
    f'down_revision = "{PREDECESSOR}"',
)
for key, suffix in (
    ("NATIVE_STATE", "native.json"),
    ("NATIVE_ADMISSION", "admission.sql"),
):
    wrapper, count = re.subn(
        key + r'_FILE = "[^"]+"',
        key + '_FILE = "' + artifacts[suffix]["name"] + '"',
        wrapper,
    )
    assert count == 1
    wrapper, count = re.subn(
        key + r'_SHA256 = "[0-9a-f]{64}"',
        key + '_SHA256 = "' + artifacts[suffix]["sha256"] + '"',
        wrapper,
    )
    assert count == 1
target = VERSIONS / "0098_um_native_selector.py"
assert not target.exists()
target.write_text(wrapper)

admission = (
    ROOT
    / "python/corpus-structure/src/corpus_structure/semantic/execution_admission.py"
)
content = admission.read_text()
assert pins["require_execution_release"] in content
content, count = re.subn(
    r'_DESCRIPTOR_SHA256 = "[0-9a-f]{64}"',
    '_DESCRIPTOR_SHA256 = "' + pins["execution_contract_descriptor"] + '"',
    content,
)
assert count == 1
content = content.replace(
    "# Frozen from reviewed migration ASTs through semantic_um_stdio_20261102.",
    "# Frozen from reviewed migration ASTs through semantic_um_selector_20261103.",
)
admission.write_text(content)
result = {
    "revision": REVISION,
    "predecessor": PREDECESSOR,
    "artifacts": artifacts,
    "pins": pins,
    "wrapper_sha256": sha256(target.read_bytes()).hexdigest(),
}
output = HERE / "raw/freeze-001.json"
assert not output.exists()
output.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
