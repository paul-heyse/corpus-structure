"""Actual evaluator CLI export and offline review of one explicitly declared cohort.

No source conversion or model operation is selected. All filenames are fresh per
attempt; a failed command and its exposure receipts remain evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
BASIS = (
    "Operator-approved PCE09 review of selected already-exposed PCE00-08 feature-fit "
    "source/output cohorts; original partitions and historical passes remain unchanged."
)


def request(run_id):
    return dict(
        run_id=run_id, source_view_id=46, include_interpretation=True, include_assessment=True,
        include_publication=True, include_support=True, max_bytes=134_217_728,
    )


def execute(command, prefix):
    with prefix.with_suffix(".stdout.json").open("xb") as stdout, prefix.with_suffix(
        ".stderr.log"
    ).open("xb") as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr, check=False)
    return dict(command=command, returncode=result.returncode,
                stdout=str(prefix.with_suffix(".stdout.json").relative_to(ROOT)),
                stderr=str(prefix.with_suffix(".stderr.log").relative_to(ROOT)))


def metrics(path):
    values = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        for label, key in (
            ("User time (seconds): ", "user_cpu_seconds"),
            ("System time (seconds): ", "system_cpu_seconds"),
            ("Maximum resident set size (kbytes): ", "peak_resident_kib"),
            ("Elapsed (wall clock) time (h:mm:ss or m:ss): ", "elapsed_wall"),
        ):
            if line.startswith(label):
                value = line[len(label):]
                values[key] = value if key == "elapsed_wall" else float(value)
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--structural-run", type=int, action="append", required=True)
    parser.add_argument("--group-set", type=int, action="append", required=True)
    parser.add_argument("--paired", action="store_true")
    parser.add_argument("--max-bytes", type=int, default=536_870_912)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", args.attempt):
        raise ValueError("attempt must be a simple fresh filename component")
    name = "combined_" + args.attempt
    bundle = RAW / name
    selected = dict(
        selections=[request(run) for run in ([31, 43, 45] if args.paired else [43, 45])],
        structural_selections=[dict(run_id=run, include_publication=True,
                                   include_support=True, max_bytes=8_000_000)
                               for run in args.structural_run],
        selected_evaluation_ids=([18, 19] if args.paired else []) + list(range(26, 31)),
        comparisons=[dict(baseline_evaluation_id=18, revised_evaluation_id=19)]
        if args.paired else [],
        max_bytes=args.max_bytes,
    )
    inputs = RAW / (name + "_selection.json")
    with inputs.open("x") as stream:
        json.dump(selected, stream, indent=2)
        stream.write("\n")
    missing = {**selected, "selections": [item for item in selected["selections"]
                                          if item["run_id"] != 43]}
    missing_inputs = RAW / (name + "_missing_selection.json")
    with missing_inputs.open("x") as stream:
        json.dump(missing, stream, indent=2)
        stream.write("\n")
    sets = ([11] if args.paired else []) + list(range(18, 23))
    common = ["--project", "m1-source-grinstead-snell", "--group-project",
              "pce-statistics-structural", "--authorization-basis", BASIS, "--json"]
    for set_id in sets:
        common += ["--assessment-set", str(set_id)]
    for set_id in args.group_set:
        common += ["--group-assessment-set", str(set_id)]
    missing_destination = RAW / (name + "_missing")
    negative = execute(["uv", "run", "ci", "review", "export-evaluated",
                        str(missing_inputs), str(missing_destination), *common],
                       RAW / (name + "_missing"))
    detail = (ROOT / negative["stdout"]).read_text()
    negative_passed = (negative["returncode"] == 1 and not missing_destination.exists()
                       and "assessment producer closure missing" in detail)
    report = dict(scope="explicit selected exposed development review; no population claim",
                  structural_runs=args.structural_run, group_sets=args.group_set,
                  missing_producer=dict(**negative, expected_refusal_passed=negative_passed))
    if not negative_passed:
        report["outcome"] = "failed"
    else:
        timing = RAW / (name + ".time.txt")
        complete = execute(["/usr/bin/time", "-v", "-o", str(timing), "uv", "run", "ci",
                            "review", "export-evaluated", str(inputs), str(bundle), *common],
                           RAW / (name + "_export"))
        report["export"] = complete
        report["resources"] = metrics(timing)
        if complete["returncode"] == 0:
            verified = execute(["uv", "run", "ci", "review", "verify", str(bundle), "--json"],
                               RAW / (name + "_verify"))
            walked = execute(["uv", "run", "python", str(ROOT / "combined_detached_walkthrough.py"),
                              str(bundle)], RAW / (name + "_walkthrough"))
            report.update(verification=verified, walkthrough=walked,
                          export_bytes=sum(path.stat().st_size for path in bundle.iterdir()),
                          outcome="passed" if verified["returncode"] == walked["returncode"] == 0
                          else "failed")
        else:
            report["outcome"] = "failed"
    with (RAW / (name + "_receipt.json")).open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(report))
    return 0 if report["outcome"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
