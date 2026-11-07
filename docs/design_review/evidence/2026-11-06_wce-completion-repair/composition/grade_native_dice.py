"""Grade the exact completed native scoped source124 result against the frozen dice frame."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

from sqlalchemy import text

from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.settings import Settings

from compare import GS, HERE, REF, discovered, edges

sys.path.insert(0, str(GS / "current-structural-journey"))
from journey_support import completed_metadata, retain  # noqa: E402


def read_source(settings, args):
    source = 124
    method = ScopedRelationsMethod.name
    with open_runtime_engine(settings, "wce-r15-dice-grade", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            run = completed_metadata(conn, args.run_id)
            if run["cut_id"] != args.cut_id or run["release_id"] != args.release_id:
                raise ValueError("native cut or release differs from selected exact completed run")
            report = dict(conn.execute(text(
                "SELECT t.id AS selected_task_id, member.origin_task_id, r.body, "
                "m.version AS operation_version, job.runtime_id AS producing_runtime "
                "FROM ops.cut_task member "
                "JOIN ops.task t ON t.id=member.task_id "
                "JOIN ops.task origin ON origin.id=member.origin_task_id "
                "JOIN ops.task_result r ON r.task_id=origin.id "
                "JOIN ops.method_config cfg ON cfg.id=origin.method_config_id "
                "JOIN ops.method m ON m.id=cfg.method_id "
                "JOIN ops.run job ON job.id=origin.run_id "
                "WHERE member.cut_id=:cut AND t.run_id=:run AND t.unit_id=:source "
                "AND t.unit_type='source_view' AND m.name=:method"
            ), {"cut": args.cut_id, "run": args.run_id, "source": source, "method": method}).mappings().one())
            req = ContributionRequest(
                run_id=args.run_id, source_view_id=source, method=method,
                include_interpretation=True, page_bytes=16_000_000, max_bytes=128_000_000,
                limit=1000,
            )
            pages, current = [], req
            while True:
                page = serve_contributions(conn, current)
                payload = page.model_dump(mode="json")
                if payload["run_id"] != args.run_id or payload["cut_id"] != args.cut_id:
                    raise ValueError("ordinary Reader returned a foreign source cut")
                pages.append(payload)
                if page.next_cursor is None:
                    break
                current = req.model_copy(update={"cursor": page.next_cursor})
    native_ids = {c["contribution_id"] for c in report["body"]["contributions"]}
    reader_ids = {
        item["row"]["contribution_id"] for page in pages for item in page["items"]
        if item["population"] == "contribution"
    }
    if not native_ids or reader_ids != native_ids:
        raise ValueError("ordinary Reader contribution population differs from exact native result")
    return run, report, pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--cut-id", type=int, required=True)
    parser.add_argument("--release-id", required=True)
    args = parser.parse_args()
    output = HERE / f"native-dice-{args.run_id}-{args.cut_id}"
    run, report, pages = read_source(Settings(), args)
    ref_bytes = REF.read_bytes()
    ref = json.loads(ref_bytes)
    actual = edges(report["body"]["contributions"])
    case_by_id = {c["id"]: c for c in ref["cases"]}
    grades = []
    for case in ref["cases"]:
        if case["family"] != "scoped_table_composition" or case["judgment"] != "supported":
            continue
        excluded = case_by_id[f"GS120-WCE-R15-DICE-CROSS-{case['id'].rsplit('-', 1)[-1]}"]
        grade = discovered(case, excluded, actual, ref["anchors"])
        grades.append({"case_id": case["id"], **grade})
    assert len(grades) == 4
    passed = all(not item["missing_edges"] and not item["counts"].get("unsupported") for item in grades)
    result = {
        "protocol": "wce-r15-native-dice-source-judgment-1",
        "run": run,
        "source_view_id": 124,
        "selected_task_id": report["selected_task_id"],
        "origin_task_id": report["origin_task_id"],
        "operation_version": report["operation_version"],
        "producing_runtime": report["producing_runtime"],
        "source_reference_sha256": sha256(ref_bytes).hexdigest(),
        "raw_report_sha256": sha256(canonical_bytes(report["body"])).hexdigest(),
        "ordinary_reader_pages": len(pages),
        "ordinary_reader_contributions": len(report["body"]["contributions"]),
        "grades": grades,
        "outcome": "passed" if passed else "failed",
    }
    retain(output / "scoped-result.json", report)
    retain(output / "assessment.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "grades"}), flush=True)
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
