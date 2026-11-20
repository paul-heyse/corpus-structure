"""Request managed stop only after observing CUDA work owned by the exact capture."""

import json
import subprocess
from pathlib import Path
from time import monotonic

from prepare import DESTINATION, EVIDENCE, ROOT

BASIS = EVIDENCE / "2026-11-19_udm20-regional-confirmation"
CLI = ROOT / "build/udm20-regional/ci-stage-frozen-n36"


def run(tool, *args):
    return subprocess.run(
        [str(tool), *map(str, args)], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def subtree(pid):
    links = [tuple(map(int, row.split())) for row in run("ps", "-eo", "pid=,ppid=").splitlines()]
    owners = {pid}
    while new := {child for child, parent in links if parent in owners} - owners:
        owners.update(new)
    return owners


def active_gpu(owners):
    rows = run("nvidia-smi", "pmon", "-s", "u", "-c", 1).splitlines()
    return [
        tuple(row.split()[:5])
        for row in rows
        if not row.startswith("#")
        and (fields := row.split())
        and len(fields) >= 5
        and fields[1].isdigit()
        and int(fields[1]) in owners
        and fields[2] == "C"
        and fields[3].isdigit()
        and int(fields[3]) > 0
    ]


def write(name, payload):
    (DESTINATION / name).write_text(json.dumps(payload, indent=2) + "\n")


def main():
    log = DESTINATION / "capture.stderr.log"
    basis = json.loads((BASIS / "raw/n36-standard-release.json").read_text())
    start = monotonic()
    observed = []
    result = None
    watch_stop = None
    command = [
        str(CLI),
        "ingest",
        "--source-root",
        basis["source_root"],
        "--request",
        str(DESTINATION / "request.json"),
        "--execution-policy",
        str(BASIS / "regional-execution-policy.json"),
        "--json",
    ]
    with (
        log.open("w") as stderr,
        (DESTINATION / "capture.json").open("w") as stdout,
        subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr) as process,
    ):
        print(f"Managed capture process {process.pid}", flush=True)
        while process.poll() is None:
            result = result or next(
                (
                    line.split()[1]
                    for line in log.read_text().splitlines()
                    if line.startswith("Result ")
                ),
                None,
            )
            if result is None:
                active_gpu({process.pid})
                continue
            owners = subtree(process.pid)
            observed = active_gpu(owners)
            if observed:
                write(
                    "cuda-at-stop.json",
                    {"result": result, "process": process.pid, "observed": observed},
                )
                print(f"Observed owned CUDA activity for {result}", flush=True)
                watch_stop = json.loads(
                    run(
                        CLI,
                        "results",
                        "stop",
                        result,
                        "--reason",
                        "UDM-27 actual capture retirement proof",
                        "--json",
                    )
                )
                write("stop-request.json", watch_stop)
                repeated = json.loads(
                    run(
                        CLI,
                        "results",
                        "stop",
                        result,
                        "--reason",
                        "UDM-27 read managed drain standing",
                        "--json",
                    )
                )
                write("stop-repeat.json", repeated)
                break
        exit_code = process.wait()
    assert result is not None
    settled = json.loads(run(CLI, "results", "inspect", result, "--json"))
    write("settled.json", settled)
    owner_pids = {int(row[1]) for row in observed}
    gpu_pids = {
        int(row.split(",")[0])
        for row in run(
            "nvidia-smi", "--query-compute-apps=pid,used_gpu_memory", "--format=csv,noheader"
        ).splitlines()
        if row.split(",")[0].isdigit()
    }
    retirement = {
        "result": result,
        "elapsed_seconds": monotonic() - start,
        "exit_code": exit_code,
        "observed_cuda_owners": sorted(owner_pids),
        "remaining_gpu_owners": sorted(gpu_pids & owner_pids),
        "remaining_processes": sorted(pid for pid in owner_pids if Path(f"/proc/{pid}").exists()),
        "managed_state": json.loads(
            run(
                CLI,
                "results",
                "stop",
                result,
                "--reason",
                "UDM-27 read terminal retirement standing",
                "--json",
            )
        ),
    }
    write("retirement.json", retirement)
    assert observed and watch_stop is not None, (
        "capture ended before owned CUDA activity was observed"
    )
    assert watch_stop["state"] in {"stop_requested", "draining"}, watch_stop
    assert retirement["managed_state"]["state"] == "confirmed_retirement", retirement
    assert not retirement["remaining_gpu_owners"] and not retirement["remaining_processes"], (
        retirement
    )
    print(json.dumps(retirement, indent=2), flush=True)


if __name__ == "__main__":
    main()
