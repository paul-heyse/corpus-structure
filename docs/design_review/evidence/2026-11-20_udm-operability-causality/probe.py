"""Isolate the source inputs to the N42 PDF transform asset fingerprint."""

import argparse
import io
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path("python/corpus-structure/src/corpus_structure")
BASE = "2bf51bf28"
M1_EDIT = "7bef656ee"
EVENT_EDIT = "1e07948ff"
M1_PATH = Path("semantic/m1_products.py")
EVENT_PATH = Path("evaluate/declared_operation_events.py")
TRANSFORM = Path("semantic/pdf_transforms.py")
DEFAULT_ARCHIVE = ROOT / "build/ci/ce3fa38868ab40269375d90eb90d96e4/runtime_archive.json"

CHILD = """
import json
import sys
sys.path.insert(0, sys.argv[1])
from corpus_structure.semantic.operation_code_assets import _producing_code
from corpus_structure.semantic import pdf_transforms as pdf

entries = (
    pdf.PreparedPdfTransform.transform,
    pdf.PreparedPdfTransform.recognize,
    pdf.execute_pdf_organization,
    pdf.execute_pdf_enrichment,
    pdf.execute_pdf_integration,
    pdf.execute_pdf_observation,
)
code = _producing_code(entries)
asset = pdf.pdf_transform_assets(json.load(sys.stdin))
print(json.dumps({
    "asset_sha256": asset.digest,
    "observed_sha256": code.observed_digest,
    "complete": code.complete,
    "module_count": len(code.modules),
    "unknown_count": len(code.unknowns),
    "meaning": json.loads(code.meaning),
}))
"""


def git(*arguments):
    return subprocess.check_output(["git", "-C", str(ROOT), *arguments])


def captured(package, record):
    result = subprocess.run(
        [sys.executable, "-I", "-c", CHILD, str(package.parent)],
        input=json.dumps(record),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def compare(base, candidate):
    old = base["meaning"]
    new = candidate.pop("meaning")
    old_modules, new_modules = (dict(basis.get("modules", ())) for basis in (old, new))
    return {
        **candidate,
        "changed_basis_fields": sorted(
            key for key in old.keys() | new.keys() if old.get(key) != new.get(key)
        ),
        "changed_observed_modules": sorted(
            key
            for key in old_modules.keys() | new_modules.keys()
            if old_modules.get(key) != new_modules.get(key)
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", default=DEFAULT_ARCHIVE, type=Path)
    args = parser.parse_args()
    archive = {item["name"]: item for item in json.loads(args.archive.read_text())["inputs"]}
    custody = archive["runtime-transport/pdf-integrated/execution-custody"]
    record = json.loads(bytes.fromhex(custody["content_hex"]))
    expected = archive["data-operations/contracts/pdf-integrated/profile-assets"]["sha256"]

    with TemporaryDirectory(prefix="udm-pdf-causality-") as temporary:
        root = Path(temporary)
        source = root / "original"
        with tarfile.open(fileobj=io.BytesIO(git("archive", BASE, str(PACKAGE)))) as tar:
            tar.extractall(source, filter="data")
        package = source / PACKAGE
        base = captured(package, record)
        relocated = root / "relocated" / "corpus_structure"
        shutil.copytree(package, relocated)
        results = {"identical_bytes_relocated": compare(base, captured(relocated, record))}
        for label, edits in (
            ("m1_edit_only", ((M1_PATH, M1_EDIT),)),
            ("event_edit_only", ((EVENT_PATH, EVENT_EDIT),)),
            ("both_edits", ((M1_PATH, M1_EDIT), (EVENT_PATH, EVENT_EDIT))),
        ):
            for path, commit in edits:
                (relocated / path).write_bytes(git("show", f"{commit}:{PACKAGE / path}"))
            results[label] = compare(base, captured(relocated, record))
            for path, _ in edits:
                (relocated / path).write_bytes((package / path).read_bytes())

        transform = relocated / TRANSFORM
        text = transform.read_text()
        before = "def execute_pdf_integration(receiver, capture, observations):\n"
        assert text.count(before) == 1
        transform.write_text(text.replace(before, before + "    observations = None\n"))
        results["transform_callable_edit"] = compare(base, captured(relocated, record))

        changed_material = {**record, "input_operation": "probe:changed-capture-operation"}
        results["declared_input_change"] = compare(base, captured(package, changed_material))

    output = {
        "baseline_commit": BASE,
        "archive_asset_sha256": expected,
        "baseline": {key: value for key, value in base.items() if key != "meaning"},
        "variants": results,
    }
    print(json.dumps(output, indent=2))
    assert base["asset_sha256"] == expected, "baseline differs from retained archive"
    assert results["identical_bytes_relocated"]["asset_sha256"] == expected
    assert results["transform_callable_edit"]["asset_sha256"] != expected
    assert results["declared_input_change"]["asset_sha256"] != expected


if __name__ == "__main__":
    main()
