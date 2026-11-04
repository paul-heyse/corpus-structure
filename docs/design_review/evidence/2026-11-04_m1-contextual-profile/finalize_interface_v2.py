"""Settle the existing sampler's observed identities after a v2 interface command exits."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def start_ticks(pid):
    try:
        return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19])
    except FileNotFoundError:
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default="interface-002")
    parser.add_argument("--resources", type=Path, required=True)
    args = parser.parse_args()
    if (Path(args.attempt).name != args.attempt or not args.attempt.startswith("interface-")
            or args.attempt == "interface-001" or args.resources.resolve().parent != HERE):
        parser.error("new local interface attempt and resource file required; frozen001 is excluded")
    out = HERE / args.attempt
    launch = json.loads((out / "launch.json").read_text())
    observed = {(launch["identity"]["pid"], launch["identity"]["start_ticks"])}
    settlement = json.loads((out / "settlement.json").read_text())
    if settlement.get("child_identity"):
        child = settlement["child_identity"]
        observed.add((child["pid"], child["start_ticks"]))
    summaries, metadata, errors = [], [], []
    samples = incomplete = 0
    last = None
    with args.resources.open() as stream:
        for line in stream:
            row = json.loads(line)
            last = row
            if row["kind"] == "metadata":
                metadata.append(row)
            elif row["kind"] == "sample":
                samples += 1
                incomplete += not row["pss_complete"]
                errors.extend(row.get("errors", ()))
                observed.update((p["pid"], p["start_ticks"]) for p in row["processes"])
            elif row["kind"] == "summary":
                summaries.append(row)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else None
    live = [dict(pid=p, start_ticks=t) for p, t in sorted(observed) if start_ticks(p) == t]
    command = metadata[0].get("command", ()) if len(metadata) == 1 else ()
    args_map = launch["arguments"]
    command_bound = len(metadata) == 1 and metadata[0]["capture_kind"] == "wrapped_cold_start"
    command_bound &= any(Path(part).name == "run_interface_v2.py" for part in command)
    for flag, value in (("--attempt", args_map["attempt"]), ("--dataset", args_map["dataset"]),
                        ("--release-id", args_map["release_id"]), ("--source-run-id", str(args_map["source_run_id"])),
                        ("--source-cut-id", str(args_map["source_cut_id"]))):
        command_bound &= flag in command and command.index(flag) + 1 < len(command) and command[command.index(flag) + 1] == value
    exited = last is not None and last["kind"] == "command_exit"
    passed = bool(summary and summary["outcome"] == "passed" and exited and last["returncode"] == 0
                  and command_bound and not live and settlement["child_absent"] and settlement["ipc_thread_absent"])
    result = dict(outcome="passed" if passed else "failed", at=datetime.now(timezone.utc).isoformat(),
        interface_outcome=summary["outcome"] if summary else "failed_or_incomplete",
        command_bound=command_bound, command_exit=last if exited else None,
        observed_identities=len(observed), identities_still_live=live,
        resources_outcome="passed" if samples and not incomplete and not errors else "partial",
        sample_count=samples, incomplete_pss_samples=incomplete, sampling_errors=errors,
        resource_summaries=summaries, quality="not_established", adoption=False,
        limit="sampled process tree only; subinterval/reparented processes may be missed; native internal phase unobservable")
    with (out / "external-settlement.json").open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(result), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
