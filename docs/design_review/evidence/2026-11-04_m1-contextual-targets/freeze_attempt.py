"""Freeze an immutable attempt, checking dataset/origin/ledger accounting only."""

from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def main():
    name = sys.argv[1]
    if Path(name).name != name or not name.startswith("attempt-"):
        raise ValueError("one local attempt folder required")
    out = HERE / name
    if (out / "freeze.json").exists():
        raise FileExistsError(f"{name} is already immutable; use a new attempt")
    summary = json.loads((out / "summary.json").read_text())
    assert summary["outcome"] == "passed"
    data = rows(out / "training-targets.jsonl")
    origins = rows(out / "training-target-origins.jsonl")
    ledger = rows(out / "record-disposition.jsonl")
    reloads = rows(out / "reload-collation.jsonl")
    refs = json.loads((out / "feature-fit-protected.json").read_text())
    original = {r["record_id"] for u in refs for r in u["authored"]["records"]}
    represented = {e["record_id"] for e in ledger if e["emitted_requests"]}
    origin_ids = {r["record_id"] for origin in origins for alias in origin["all_alias_origins"] for r in alias["origins"]}
    assert original == {e["record_id"] for e in ledger} and len(original) == 270
    assert represented == origin_ids
    assert len(data) == len(origins) == len(reloads) == summary["examples"]
    for example, origin, reloaded in zip(data, origins, reloads, strict=True):
        assert example["output"]["sample_id"] == origin["request"] == reloaded["request"]
        assert reloaded["full_conditioning_digest"] == origin["audit"]["conditioning_digest"]
        assert reloaded["targets_digest"] == origin["audit"]["native_targets_digest"]
    (out / "freeze_attempt-executed.py.txt").write_bytes(Path(__file__).read_bytes())
    paths = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "freeze.json")
    files = []
    for path in paths:
        blob = path.read_bytes()
        files.append(dict(path=str(path.relative_to(HERE)), bytes=len(blob), sha256=sha256(blob).hexdigest()))
    record = dict(outcome="passed", immutable_attempt=name, files=files,
        original_records=len(original), represented_records=len(represented), examples=len(data),
        note="Input/output integrity and prior native metadata checks only; no model/quality/adoption claim. Working .py files intentionally excluded; executed snapshots included.")
    with (out / "freeze.json").open("x") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(dict(outcome="passed", attempt=name, files=len(files), bytes=sum(f["bytes"] for f in files),
        dataset=next(f for f in files if f["path"].endswith("/training-targets.jsonl")))))


if __name__ == "__main__":
    main()
