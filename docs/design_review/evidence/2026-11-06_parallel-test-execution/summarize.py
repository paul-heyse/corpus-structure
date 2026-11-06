"""Check this probe's observed concurrency, grouping and receipt identities."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
FOLDER = Path(__file__).resolve().parent
RECEIPT = REPO / "build/test-receipts/qualification/parallel16-compatible-20261106"
result = json.loads((RECEIPT / "classification.json").read_text())
receipt = result["receipts"][0]
assert result["status"] == "passed"
assert len(receipt["selected"]) == 40
assert len(receipt["nodes"]) == 40
assert receipt["native_provenance"]["status"] == "complete"
assert len(receipt["native_provenance"]["claimed"]) == 2
assert not receipt["stream_errors"]
assert all("@compatible_" not in node for node in receipt["selected"])
assert any("compatible@0]" in node for node in receipt["selected"])

observations = [json.loads(path.read_text()) for path in (RECEIPT / "smoke-observations").glob("case-*.json")]
groups = [json.loads(path.read_text()) for path in (RECEIPT / "group-observations").glob("case-*.json")]
workers = {row["worker"]: row["pid"] for row in observations}
assert len(workers) == len(set(workers.values())) == 16
assert len(groups) == 8
assert len({row["worker"] for row in groups}) == 1
concurrency = maximum = 0
for _, delta in sorted([(row["started"], 1) for row in observations] + [(row["finished"], -1) for row in observations]):
    concurrency += delta
    maximum = max(maximum, concurrency)
assert maximum == 16
native = [row for row in observations if row["database"]]
assert len(native) == len({row["database"] for row in native}) == 2
assert len({row["worker"] for row in native}) == 2
assert max(row["started"] for row in native) < min(row["finished"] for row in native)

reportlog = [json.loads(line) for line in (RECEIPT / "reportlog.jsonl").read_text().splitlines()]
raw_calls = [row for row in reportlog if row.get("$report_type") == "TestReport" and row["when"] == "call"]
assert len(raw_calls) == 40
assert all("@compatible_" in row["nodeid"] for row in raw_calls)
events = [json.loads(line) for path in RECEIPT.glob("events-*.jsonl") for line in path.read_text().splitlines()]
manifests = [row for row in events if row["event"] == "collection_finish"]
assert len(manifests) == 16
assert all(len(row["nodeid_aliases"]) == 40 for row in manifests)
summary = {
    "status": "passed", "pytest": receipt["invocation"]["versions"]["pytest"],
    "pytest_xdist": receipt["invocation"]["versions"]["pytest-xdist"],
    "selected_items": 40, "parallel_items": 32, "grouped_items": 8,
    "workers": workers, "maximum_overlapping_test_calls": maximum,
    "shared_group_worker": groups[0]["worker"], "native_clones": native,
    "native_provenance": receipt["native_provenance"],
    "raw_report_calls": len(raw_calls), "worker_collection_manifests": len(manifests),
    "canonical_identity_preserves_literal_at": True,
}
(FOLDER / "compatible-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
