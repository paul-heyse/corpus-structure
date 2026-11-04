"""Settle a finished epoch's observed process tree; no model or database execution."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def identity(pid):
    try:
        tail = (Path("/proc") / str(pid) / "stat").read_text().rsplit(") ", 1)[1].split()
        return int(tail[19])
    except FileNotFoundError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--resources", type=Path, required=True)
    args = parser.parse_args()
    if Path(args.attempt).name != args.attempt or not args.attempt.startswith("attempt-"):
        parser.error("attempt must name one existing local attempt-* directory")
    out = HERE / args.attempt
    if args.resources.resolve().parent != HERE:
        parser.error("resource receipt must be in this evidence folder")
    observed = set()
    last = None
    summaries = []
    samples = 0
    incomplete_pss = 0
    errors = []
    with args.resources.open() as stream:
        for line in stream:
            row = json.loads(line)
            last = row
            if row["kind"] == "sample":
                samples += 1
                incomplete_pss += not row["pss_complete"]
                errors.extend(row.get("errors", ()))
                observed.update((process["pid"], process["start_ticks"]) for process in row["processes"])
            elif row["kind"] == "summary":
                summaries.append(row)
    launch = json.loads((out / "launch.json").read_text())
    live = [dict(pid=pid, start_ticks=ticks) for pid, ticks in sorted(observed) if identity(pid) == ticks]
    runner_absent = identity(launch["pid"]) != launch["process_start_ticks"]
    result_path = out / "result.json"
    result = json.loads(result_path.read_text()) if result_path.exists() else None
    exited = last is not None and last["kind"] == "command_exit"
    numerical = result is not None and result["outcome"] == "passed"
    passed = numerical and exited and last["returncode"] == 0 and not live and runner_absent
    receipt = dict(
        outcome="passed" if passed else "failed", at=datetime.now(timezone.utc).isoformat(),
        numerical_epoch_outcome=result["outcome"] if result else "failed_or_incomplete",
        command_exit=last if exited else None, observed_identities=len(observed),
        observed_processes_still_live=live, runner_absent=runner_absent,
        resources_outcome="passed" if samples and not incomplete_pss and not errors else "partial",
        sample_count=samples, incomplete_pss_samples=incomplete_pss, sampling_errors=errors,
        resource_summaries=summaries,
        limit="observed tree identities only; sub-interval/reparented processes can be missed by polling",
        quality_claim="not_established", adoption=False,
    )
    with (out / "external-settlement.json").open("x") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(receipt, ensure_ascii=False), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
