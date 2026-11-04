"""Sample one Linux process tree without signalling it or changing its workload."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

PROC = Path("/proc")
TICKS = os.sysconf("SC_CLK_TCK")
PAGE_KIB = os.sysconf("SC_PAGE_SIZE") / 1024


def process_stat(pid):
    raw = (PROC / str(pid) / "stat").read_text()
    # comm may contain spaces and parentheses. Fields after its final ')' are fixed.
    fields = raw[raw.rindex(")") + 2:].split()
    return dict(pid=pid, ppid=int(fields[1]), state=fields[0],
                cpu_seconds=(int(fields[11]) + int(fields[12])) / TICKS,
                threads=int(fields[17]), start_ticks=int(fields[19]),
                rss_kib=int(fields[21]) * PAGE_KIB)


def tree_stats(root_pid):
    stats = {}
    errors = []
    for directory in PROC.iterdir():
        if not directory.name.isdigit():
            continue
        try:
            row = process_stat(int(directory.name))
            stats[row["pid"]] = row
        except (OSError, ValueError, IndexError) as exc:
            # /proc is not atomic. Retain discovery errors even when membership
            # cannot be determined; an unreadable child must not imply absence.
            errors.append(dict(pid=int(directory.name), operation="stat", error=str(exc)))
    selected = {root_pid} if root_pid in stats else set()
    while True:
        children = {pid for pid, row in stats.items() if row["ppid"] in selected}
        expanded = selected | children
        if expanded == selected:
            break
        selected = expanded
    return [stats[pid] for pid in sorted(selected)], errors


def memory(row):
    pid = row["pid"]
    try:
        content = (PROC / str(pid) / "smaps_rollup").read_text()
        entries = {}
        for line in content.splitlines():
            name, _, rest = line.partition(":")
            if name in {"Pss", "SwapPss"}:
                entries[name] = int(rest.split()[0])
        row["pss_kib"] = entries.get("Pss")
        row["swap_pss_kib"] = entries.get("SwapPss")
    except (OSError, ValueError, IndexError) as exc:
        row["pss_kib"] = None
        row["memory_error"] = str(exc)
    try:
        row["command"] = (PROC / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode(
            errors="replace").rstrip()
    except OSError as exc:
        row["command_error"] = str(exc)


def sample(root_pid, stream, *, interval, capture_kind, command=None):
    started = time.monotonic()
    previous = {}
    previous_time = None
    root_start = None
    peak_pss = None
    peak_rss = 0
    peak_threads = 0
    cpu_delta_total = 0.0
    samples = 0
    pss_incomplete_samples = 0
    seen = {}
    def emit(value):
        stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
    emit(dict(kind="metadata", root_pid=root_pid, capture_kind=capture_kind,
              interval_seconds=interval, command=command, utc=time.strftime(
                  "%Y-%m-%dT%H:%M:%SZ", time.gmtime()), clock_ticks_per_second=TICKS,
              memory_unit="KiB", cpu_delta_scope="consecutive observed process identities",
              limits="sampled /proc tree; short-lived or reparented children may be missed; PSS is proportional resident share; RSS sum double-counts shared pages"))
    while True:
        now = time.monotonic()
        rows, errors = tree_stats(root_pid)
        root = next((row for row in rows if row["pid"] == root_pid), None)
        if root is None or root["state"] == "Z" or (
            root_start is not None and root["start_ticks"] != root_start
        ):
            reason = "root_exited" if root is None or root["state"] == "Z" else "root_pid_reused"
            break
        root_start = root["start_ticks"]
        current = {}
        for row in rows:
            memory(row)
            identity = (row["pid"], row["start_ticks"])
            current[identity] = row["cpu_seconds"]
            seen[identity] = dict(pid=row["pid"], start_ticks=row["start_ticks"], ppid=row["ppid"])
            row["cpu_delta_seconds"] = (
                max(0.0, row["cpu_seconds"] - previous[identity])
                if identity in previous else None
            )
        cpu_delta = sum(row["cpu_delta_seconds"] or 0 for row in rows)
        elapsed = now - previous_time if previous_time is not None else None
        missing_pss = [row["pid"] for row in rows if row["pss_kib"] is None]
        pss = sum(row["pss_kib"] or 0 for row in rows)
        rss = sum(row["rss_kib"] for row in rows)
        threads = sum(row["threads"] for row in rows)
        if not missing_pss:
            peak_pss = max(peak_pss or 0, pss)
        pss_incomplete_samples += bool(missing_pss)
        peak_rss = max(peak_rss, rss)
        peak_threads = max(peak_threads, threads)
        cpu_delta_total += cpu_delta
        samples += 1
        emit(dict(kind="sample", elapsed_seconds=now-started, interval_seconds=elapsed,
                  sample_duration_seconds=time.monotonic()-now, processes=rows,
                  process_count=len(rows), threads=threads, pss_kib=pss,
                  pss_complete=not missing_pss, pss_unavailable_pids=missing_pss,
                  rss_sum_kib=rss, cpu_delta_seconds=cpu_delta,
                  cpu_equivalent_cores=cpu_delta/elapsed if elapsed else None,
                  disappeared_identities=[list(key) for key in previous.keys()-current.keys()],
                  errors=errors))
        previous, previous_time = current, now
        time.sleep(max(0.0, interval-(time.monotonic()-now)))
    emit(dict(kind="summary", reason=reason, capture_kind=capture_kind, samples=samples,
              elapsed_seconds=time.monotonic()-started, peak_complete_pss_kib=peak_pss,
              peak_rss_sum_kib=peak_rss if samples else None,
              peak_threads=peak_threads if samples else None,
              pss_incomplete_samples=pss_incomplete_samples,
              observed_cpu_delta_seconds=cpu_delta_total if samples > 1 else None,
              observed_process_identities=list(seen.values()), final_errors=errors,
              resource_qualification="not_established"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, help="Attach to an existing process (partial capture).")
    parser.add_argument("--interval", type=float, default=.5)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command after -- for cold start.")
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.interval <= 0 or (args.pid is None) == (not command):
        parser.error("choose exactly one of --pid or command; interval must be positive")
    # Refuse overwrites before launching any requested command.
    with args.out.open("x") as stream:
        child = subprocess.Popen(command) if command else None
        sample(child.pid if child else args.pid, stream, interval=args.interval,
               capture_kind="wrapped_cold_start" if child else "attached_partial", command=command or None)
        if child:
            code = child.wait()
            stream.write(json.dumps(dict(kind="command_exit", returncode=code)) + "\n")
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
