"""Reconcile every frozen source opportunity against actual retained candidates.

This reports location coverage, separate from role/attachment quality. Overlap
does not become exact capture; absent predictions remain explicit ledger rows.
"""

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_directory")
    parser.add_argument("--source", choices=("001", "002"), default="001")
    parser.add_argument("--additional-dir", action="append", default=[])
    args = parser.parse_args()
    root = HERE / args.candidate_directory
    roots = [root, *(HERE / name for name in args.additional_dir)]
    results = [(directory, json.loads((directory / "result.json").read_bytes())) for directory in roots]
    if any(result["outcome"] != "passed" for _, result in results):
        raise ValueError("assessment needs completed actual candidate execution")
    source_file = RAW / f"source-opportunities-{args.source}.json"
    source = json.loads(source_file.read_bytes())
    passages = {p["passage_id"]: p for p in source["passages"]}
    pins = {p["source_ref"]: next(s for s in source["sources"] if sha256(canonical_bytes(s)).hexdigest() == p["source_ref"]) for p in source["passages"]}
    candidates = []
    for actual_root, report in ((directory, report) for directory, result in results for report in result["runs"]):
        directory = actual_root / report["project_id"]
        page = json.loads((directory / "inspection.json").read_bytes())
        if not page["population_paging_complete"]:
            raise ValueError("selected inspection is incomplete; follow continuation before assessing")
        correspondence = {r["id"]: r for r in json.loads((directory / "source-correspondence.json").read_bytes())}
        for item in page["items"]:
            if item["population"] != "contribution":
                continue
            row = item["row"]
            if not row["semantic_type"].startswith("source_role."):
                continue
            value = source_python(row["value"])
            if value["protocol"] != "named-annotation-role-2":
                raise ValueError("unexpected role representation")
            candidates.append({"contribution_id": row["contribution_id"], "selected_task_id": row["selected_task_id"],
                "origin_task_id": row["origin_task_id"], "run_id": report["run_id"], "project_id": report["project_id"],
                "source": correspondence[row["source_view_id"]], "role": value["role"], "rule": value["rule"],
                "variant": value["variant"], "extents": value["extents"], "expansion_status": value["status"]})
    ledger = []
    for opportunity in source["opportunities"]:
        passage = passages[opportunity["passage_id"]]
        pin = pins[passage["source_ref"]]
        same_source = [c for c in candidates if c["project_id"] == pin["project_id"]
            and c["source"]["projection_digest"] == pin["projection_digest"]
            and c["source"]["native_content_digest"] == pin["native_content_digest"]]
        a, b = opportunity["start"], opportunity["end"]
        exact, overlapping = [], []
        for candidate in same_source:
            extents = candidate["extents"]
            if len(extents) == 1 and extents[0] == [a, b]:
                exact.append(candidate)
            elif any(start < b and a < end for start, end in extents):
                overlapping.append(candidate)
        ledger.append({"opportunity_id": opportunity["opportunity_id"], "facet": opportunity["facet"],
            "passage_id": opportunity["passage_id"], "start": a, "end": b, "source_text": opportunity["text"],
            "location_outcome": "exact_candidate" if exact else "overlapping_candidate_only" if overlapping else "not_captured",
            "exact_candidates": exact, "overlapping_candidates": overlapping,
            "role_judgment": "unassessed", "attachment_judgment": "unassessed",
            "reason": "Location comparison only. Retained syntactic labels are not independent semantic role or attachment support."})
    output = {"protocol": "wce-source-candidate-coverage-1", "source_packet_sha256": sha256(source_file.read_bytes()).hexdigest(),
        "execution_result_sha256": {directory.name: sha256((directory / "result.json").read_bytes()).hexdigest() for directory in roots},
        "source_opportunities": len(source["opportunities"]), "ledger": ledger,
        "counts": dict(Counter(r["location_outcome"] for r in ledger)),
        "all_opportunities_retained": len(ledger) == len(source["opportunities"]),
        "quality_claim": "declared exact source-location coverage only; no role, attachment, applicability, calibration or whole-record claim",
        "native_reference_eligibility": False}
    with (root / "source-coverage.json").open("xb") as stream:
        stream.write(canonical_bytes(output) + b"\n")
    print(json.dumps({"outcome": "passed", "source_opportunities": len(ledger), "counts": output["counts"]}))


if __name__ == "__main__":
    main()
