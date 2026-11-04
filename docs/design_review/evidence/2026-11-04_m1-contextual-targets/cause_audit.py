"""Retain every excluded C reading and its exact request/role blockers."""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def main():
    out = HERE / (sys.argv[1] if len(sys.argv) > 1 else "attempt-001")
    ledger = rows(out / "record-disposition.jsonl")
    audits = {row["request"]: row for row in rows(out / "request-audit.jsonl")}
    conflicts = {row["request"]: row for row in rows(out / "conditioning-conflicts.jsonl")}
    refs = json.loads((out / "feature-fit-protected.json").read_text())
    records = {r["record_id"]: r for ref in refs for r in ref["authored"]["records"]}
    stage_counts = defaultdict(Counter)
    result = []
    for entry in ledger:
        if entry["emitted_requests"]:
            continue
        complete = entry["mapped_requests"]
        initially_collated = [request for request in complete if audits[request]["status"] == "collated"]
        stage = "conditioning" if initially_collated else "whole_request" if complete else "exact_mapping"
        stage_counts[entry["family"]][stage] += 1
        role_failures = []
        for error in entry["excluded_requests"]:
            reason = error.get("reason", "")
            if reason.startswith("["):
                for failure in json.loads(reason):
                    role_failures.append(dict(request=error["request"], **failure))
            elif "formula population source mapping" in reason:
                role_failures.append(dict(request=error["request"], role="formula", reason=reason))
        record = records[entry["record_id"]]
        anchors = {a["anchor_id"]: a for a in record["anchors"]}
        source_roles = []
        for evidence in record["evidence_sets"]:
            for identity in evidence["anchors"]:
                anchor = anchors[identity]
                source_roles.append(dict(role=evidence["role"], usage=evidence["usage"], anchor_id=identity,
                    source_view_id=anchor["pin"]["source_view_id"], space=anchor["space"], pointer=anchor["pointer"],
                    start=anchor.get("start"), end=anchor.get("end"),
                    quote_sha256=sha256(anchor.get("source_piece", "").encode()).hexdigest()))
        result.append(dict(record_id=entry["record_id"], family=entry["family"], original_pin=entry["original_pin"],
            terminal_stage=stage, own_role_failures=role_failures, source_roles=source_roles,
            mapped_request_blockers=[dict(request=request, errors=audits[request]["errors"],
                mapped=audits[request]["mapped"], outside_population=audits[request]["outside_population"])
                for request in complete if audits[request]["status"] != "collated"],
            conditioning_refusals=[conflicts[request] for request in initially_collated],
            outside_population=entry["outside_population"], assembly_exclusions=entry["assembly_exclusions"]))
    with (out / "exclusion-causes.jsonl").open("x") as stream:
        for row in result:
            stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    with (out / "exclusion-cause-summary.json").open("x") as stream:
        json.dump(dict(excluded=len(result), family_terminal_stage={f: dict(c) for f, c in stage_counts.items()},
            note="Stages are exclusive; multiple exact blockers per request remain in exclusion-causes.jsonl."), stream, indent=2)
        stream.write("\n")
    (out / "cause_audit-executed.py.txt").write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(excluded=len(result), family_terminal_stage={f: dict(c) for f, c in stage_counts.items()})))


if __name__ == "__main__":
    main()
