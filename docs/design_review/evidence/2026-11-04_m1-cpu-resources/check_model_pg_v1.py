"""Bounded benign-child combined sampler and owned-child failure controls."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SAMPLER = HERE / "sample_model_pg_v1.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    if not args.tag.isalnum():
        parser.error("tag must be one new alphanumeric token")
    output = HERE / f"combined-smoke-{args.tag}.jsonl"
    failure_output = HERE / f"combined-owned-settlement-{args.tag}.jsonl"
    marker = HERE / f"combined-owned-child-{args.tag}.json"
    receipt = HERE / f"combined-sanity-{args.tag}.json"
    for path in (output, failure_output, marker, receipt):
        if path.exists():
            raise FileExistsError(path)
    base_hash = sha256((HERE / "sample_tree.py").read_bytes()).hexdigest()
    leaf = "import time;data=bytearray(8*1024*1024);end=time.monotonic()+1.3\nwhile time.monotonic()<end: pass"
    parent = ("import subprocess,sys,time;data=bytearray(8*1024*1024);"
        f"child=subprocess.Popen([sys.executable,'-B','-c',{leaf!r}]);child.wait();time.sleep(.3)")
    command = [sys.executable, "-B", str(SAMPLER), "--sudo-reader", "--interval", ".1", "--out", str(output),
        "--", sys.executable, "-B", "-c", parent]
    completed = subprocess.run(command, check=False)
    assert completed.returncode == 0
    events = [json.loads(line) for line in output.read_text().splitlines()]
    samples = [row for row in events if row["kind"] == "sample"]
    ready = next(row for row in events if row["kind"] == "observer_ready")
    launch = next(row for row in events if row["kind"] == "workload_launch")
    summary = next(row for row in events if row["kind"] == "summary")
    settlement = next(row for row in events if row["kind"] == "controller_settlement")
    assert ready["observer_euid"] == 0 and ready["postgres_pss_readable"]
    assert launch["uid"] != 0 and launch["observer_ready_before_launch"]
    assert any(row["groups"]["model"]["process_count"] >= 2 for row in samples)
    complete = [row for row in samples if row["groups"]["combined"]["pss_complete"]]
    assert complete
    assert all(not row["model_uid_violations"] and not row["overlapping_group_pids"] for row in samples)
    assert all(row["groups"]["combined"]["known_pss_sum_kib"] ==
        row["groups"]["model"]["known_pss_sum_kib"] + row["groups"]["postgres"]["known_pss_sum_kib"] for row in samples)
    assert any(row["groups"]["model"]["cpu_delta_seconds"] > 0 for row in samples)
    assert any(row["model_root_alive"] and row["postgres_root"]["available"] for row in samples)
    assert not samples[-1]["model_root_alive"] and samples[-1]["postgres_root"]["available"]
    assert summary["reason"] == "model_root_exited_or_unavailable"
    assert settlement["observer_returncode"] == settlement["workload_returncode"] == 0
    assert settlement["capture_failure"] is None and not settlement["settlement_errors"]
    assert summary["resource_qualification"] == "not_established"
    refused = subprocess.run(command, capture_output=True, text=True, check=False)
    assert refused.returncode != 0 and "FileExistsError" in refused.stderr
    # Inject only an observer protocol failure. The observed benign child is real
    # and must finish normally before the controller returns. This is not PG data.
    spec = importlib.util.spec_from_file_location("combined_sampler_failure_control", SAMPLER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    actual_popen = subprocess.Popen
    shim = "import json,time;print(json.dumps(" + repr(dict(kind="observer_ready", observer_euid=__import__("os").geteuid(),
        postgres_pss_readable=True, script_sha256=module.file_hash(SAMPLER), base_sampler_sha256=base_hash)) + "),flush=True);time.sleep(.1);print('MALFORMED',flush=True);time.sleep(.1)"

    def controlled_popen(argv, *pos, **kwargs):
        if "--reader" in argv:
            return actual_popen([sys.executable, "-B", "-c", shim], *pos, **kwargs)
        return actual_popen(argv, *pos, **kwargs)

    module.subprocess.Popen = controlled_popen
    benign = "import json,os,time;from pathlib import Path;time.sleep(.6);Path(" + repr(str(marker)) + ").write_text(json.dumps({'uid':os.geteuid(),'completed':True}))"
    control_args = argparse.Namespace(out=failure_output, sudo_reader=False, interval=.1, max_seconds=None,
        pid=None, allow_partial_postgres=False)
    began = time.monotonic()
    try:
        code = module.controller(control_args, [sys.executable, "-B", "-c", benign])
    finally:
        module.subprocess.Popen = actual_popen
    elapsed = time.monotonic() - began
    failure_events = [json.loads(line) for line in failure_output.read_text().splitlines()]
    failure_settlement = next(row for row in failure_events if row["kind"] == "controller_settlement")
    assert code == 125 and failure_settlement["capture_failure"]["type"] == "JSONDecodeError"
    assert failure_settlement["workload_returncode"] == 0 and failure_settlement["observer_returncode"] == 0
    assert marker.exists() and json.loads(marker.read_text())["uid"] != 0 and elapsed >= .6
    assert sha256((HERE / "sample_tree.py").read_bytes()).hexdigest() == base_hash
    result = dict(outcome="passed", command=command, real_combined_samples=len(samples), complete_combined_samples=len(complete),
        normal_uid_workload=True, readonly_root_observer=True, pg_still_live_at_observer_settlement=True,
        pg_root_identities=summary["postgres_root_identities"], overwrite_refused=True,
        malformed_observer_real_child_waited=True, failure_control_seconds=elapsed,
        sampler_sha256=module.file_hash(SAMPLER), existing_sampler_sha256=base_hash,
        scope="Benign Python parent/child plus readonly live PG /proc; synthetic observer failure for owned-child settlement. No model, DB connection/write, service action or capacity qualification.")
    with receipt.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
