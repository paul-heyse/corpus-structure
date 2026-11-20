"""Compare current selected executable capture in isolated source copies.

Run with uv run python PATH. Output is a compact JSON document. This exercises
actual selected callable capture and profile-asset construction, without native
admission, database operations or provider inference. It cannot establish full
runtime equivalence. Historical patches that no longer apply are recorded.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "python/corpus-structure/src/corpus_structure"
ARCHIVE = ROOT / "build/ci/ce3fa38868ab40269375d90eb90d96e4/runtime_archive.json"
CHILD = '''
import json
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from corpus_structure.semantic import pdf_transforms as pdf
from corpus_structure.semantic.operation_code_assets import _producing_code
spec = pdf.pdf_transform_specification("integrated")
captured = spec.capture(Path(pdf.__file__).parents[1])
code = _producing_code(tuple(function for _, function in spec.functions))
asset = pdf.pdf_transform_assets(json.load(sys.stdin))
print(json.dumps({
    "digest": asset.digest,
    "reuse_eligible": asset.reuse_eligible,
    "complete": code.complete,
    "unknowns": len(code.unknowns),
    "functions": [owner for owner, _ in spec.functions],
    "captured": [source.module for source in captured.sources],
}))
'''


def acquire(package, record):
    process = subprocess.run(
        [sys.executable, "-I", "-c", CHILD, str(package.parent)],
        input=json.dumps(record), text=True, capture_output=True, check=True,
    )
    return json.loads(process.stdout)


def main():
    archive = json.loads(ARCHIVE.read_text())
    custody = next(
        item for item in archive["inputs"]
        if item["name"] == "runtime-transport/pdf-integrated/execution-custody"
    )
    record = json.loads(bytes.fromhex(custody["content_hex"]))
    with tempfile.TemporaryDirectory(prefix="dmo01-selected-") as temporary:
        selected = Path(temporary) / "first/corpus_structure"
        shutil.copytree(PACKAGE, selected, ignore=shutil.ignore_patterns("__pycache__"))
        sources = {
            str(path.relative_to(selected)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in selected.rglob("*.py")
        }
        baseline = acquire(selected, record)
        moved = Path(temporary) / "second/corpus_structure"
        shutil.copytree(selected, moved)
        variants = {"relocated": acquire(moved, record)}
        assert variants["relocated"] == baseline
        for label, path, commit in (
            ("m1", "semantic/m1_products.py", "7bef656ee"),
            ("event", "evaluate/declared_operation_events.py", "1e07948ff"),
        ):
            patch = subprocess.check_output(
                ["git", "-C", str(ROOT), "diff", commit + "^", commit, "--",
                 "python/corpus-structure/src/corpus_structure/" + path], text=True,
            )
            target = moved / path
            before = target.read_bytes()
            applied = subprocess.run(
                ["patch", "-R", "--batch", "--silent", str(target)],
                input=patch, text=True, capture_output=True,
            )
            if applied.returncode:
                variants[label] = {"patch": "unavailable", "reason": "historical hunk no longer applies"}
            else:
                variants[label] = acquire(moved, record)
            target.write_bytes(before)
        target = moved / "semantic/pdf_transforms.py"
        before = target.read_text()
        marker = "def execute_pdf_integration(receiver, capture, observations):\n"
        assert before.count(marker) == 1
        target.write_text(before.replace(marker, marker + "    observations = None\n", 1))
        variants["changed_transform"] = acquire(moved, record)
        assert variants["changed_transform"]["digest"] != baseline["digest"]
        target.write_text(before)
        variants["changed_input"] = acquire(
            moved, {**record, "input_operation": "probe:changed-declared-input"}
        )
        assert variants["changed_input"]["digest"] != baseline["digest"]
    print(json.dumps({
        "source_commit": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "captured_source_hashes": sources,
        "baseline": baseline,
        "variants": variants,
        "limits": "Selected capture and asset construction only. Native admission, provider execution and full runtime equivalence were not exercised.",
    }, indent=2))


if __name__ == "__main__":
    main()
