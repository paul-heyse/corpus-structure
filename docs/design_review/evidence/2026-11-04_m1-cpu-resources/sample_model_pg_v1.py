"""Sample a normal-user workload tree plus dedicated PG18/corpus, without DB access.

The optional sudo process is a read-only /proc observer. It never launches the
workload, opens a database connection, changes a service or signals either tree.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import select
import subprocess
import sys
import time
from typing import TypedDict

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE / "sample_tree.py"
PG_DIRECTORY = Path("/var/lib/postgresql/18/corpus")
PG_PIDFILE = PG_DIRECTORY / "postmaster.pid"


class Peak(TypedDict):
    pss: int | None
    rss: float
    threads: int
    cpu: float
    incomplete: int


def load_base():
    spec = importlib.util.spec_from_file_location("existing_m1_proc_sampler", BASE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def emit(stream, value):
    stream.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")
    stream.flush()


def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()


def discover(base):
    stats, errors = {}, []
    for directory in base.PROC.iterdir():
        if not directory.name.isdigit():
            continue
        pid = int(directory.name)
        try:
            row = base.process_stat(pid)
            row["uid"] = directory.stat().st_uid
            row["stat_observed_monotonic_ns"] = time.monotonic_ns()
            stats[pid] = row
        except (OSError, ValueError, IndexError) as error:
            errors.append(dict(pid=pid, operation="discovery_stat", type=type(error).__name__, error=str(error)))
    return stats, errors


def descendants(stats, root):
    selected = {root} if root in stats else set()
    while True:
        expanded = selected | {pid for pid, row in stats.items() if row["ppid"] in selected}
        if expanded == selected:
            return selected
        selected = expanded


def postgres_root(stats):
    start = time.monotonic_ns()
    try:
        lines = PG_PIDFILE.read_text().splitlines()
        pid = int(lines[0])
        if lines[1] != str(PG_DIRECTORY) or int(lines[3]) != 5434 or pid < 1:
            raise ValueError("dedicated cluster PID-file identity differs")
        root = stats[pid]
        command = (Path("/proc") / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if "postgres" not in command or str(PG_DIRECTORY) not in command:
            raise ValueError("PID-file process does not identify the selected postmaster")
        return dict(available=True, pid=pid, start_ticks=root["start_ticks"], uid=root["uid"],
            data_directory=lines[1], port=int(lines[3]), pidfile_start_epoch=lines[2], command=command.rstrip(),
            read_start_ns=start, read_end_ns=time.monotonic_ns())
    except (OSError, ValueError, IndexError, KeyError) as error:
        return dict(available=False, pidfile=str(PG_PIDFILE), type=type(error).__name__, error=str(error),
            read_start_ns=start, read_end_ns=time.monotonic_ns())


def observe_memory(base, row):
    row["memory_read_start_ns"] = time.monotonic_ns()
    base.memory(row)
    try:
        after = base.process_stat(row["pid"])
        row["identity_revalidated"] = after["start_ticks"] == row["start_ticks"]
        if not row["identity_revalidated"]:
            row["pss_kib"] = None
            row["swap_pss_kib"] = None
            row["memory_error"] = "PID/start identity changed during memory collection"
    except (OSError, ValueError, IndexError) as error:
        row["identity_revalidated"] = False
        row["pss_kib"] = None
        row["memory_error"] = str(error)
    row["memory_read_end_ns"] = time.monotonic_ns()


def totals(rows, *, available, discovery_complete, elapsed):
    missing = [row["pid"] for row in rows if row.get("pss_kib") is None or not row["identity_revalidated"]]
    observed_complete = available and bool(rows) and not missing
    complete = observed_complete and discovery_complete
    known = sum(row.get("pss_kib") or 0 for row in rows)
    cpu = sum(row["cpu_delta_seconds"] or 0 for row in rows)
    return dict(process_count=len(rows), threads=sum(row["threads"] for row in rows),
        known_pss_sum_kib=known, pss_kib=known if complete else None,
        observed_pss_complete=observed_complete, membership_discovery_complete=available and discovery_complete,
        pss_complete=complete, pss_unavailable_pids=missing,
        rss_sum_kib=sum(row["rss_kib"] for row in rows), cpu_delta_seconds=cpu,
        cpu_equivalent_cores=cpu / elapsed if elapsed else None,
        cpu_delta_missing_identities=[dict(pid=row["pid"], start_ticks=row["start_ticks"])
            for row in rows if row["cpu_delta_seconds"] is None])


def reader(args):
    base = load_base()
    stats, errors = discover(base)
    pg = postgres_root(stats)
    pg_pss = False
    if pg["available"]:
        root = dict(stats[pg["pid"]])
        observe_memory(base, root)
        pg_pss = root.get("pss_kib") is not None and root["identity_revalidated"]
    emit(sys.stdout, dict(kind="observer_ready", observer_pid=os.getpid(), observer_euid=os.geteuid(),
        postgres=pg, postgres_pss_readable=pg_pss, discovery_errors=errors,
        script_sha256=file_hash(Path(__file__)), base_sampler_sha256=file_hash(BASE)))
    binding = json.loads(sys.stdin.readline())
    if binding.get("abort"):
        return 0
    model_pid, expected_start, expected_uid = binding["model_pid"], binding.get("model_start_ticks"), binding["workload_uid"]
    launch_ns = binding["launch_monotonic_ns"]
    previous, previous_time, seen = {}, None, {}
    peaks: dict[str, Peak] = {name: dict(pss=None, rss=0.0, threads=0, cpu=0.0, incomplete=0)
        for name in ("model", "postgres", "combined")}
    samples, first_ns, pg_identities = 0, None, set()
    reason = "reader_error"
    while True:
        cycle_start = time.monotonic_ns()
        stats, errors = discover(base)
        pg = postgres_root(stats)
        model = stats.get(model_pid)
        live = model is not None and model["state"] != "Z"
        if model is not None and (model["uid"] != expected_uid or expected_uid == 0):
            live, reason = False, "workload_uid_changed_or_root"
        elif model is not None and expected_start is not None and model["start_ticks"] != expected_start:
            live, reason = False, "model_pid_reused"
        elif not live:
            reason = "model_root_exited_or_unavailable"
        if live and expected_start is None:
            assert model is not None
            expected_start = model["start_ticks"]
        model_set = descendants(stats, model_pid) if live else set()
        pg_set = descendants(stats, pg["pid"]) if pg["available"] else set()
        current = {}
        rows = []
        for pid in sorted(model_set | pg_set):
            row = dict(stats[pid])
            observe_memory(base, row)
            identity = (pid, row["start_ticks"])
            before = previous.get(identity)
            delta = row["cpu_seconds"] - before if before is not None else None
            row["cpu_delta_seconds"] = delta if delta is not None and delta >= 0 and row["identity_revalidated"] else None
            row["cpu_counter_regressed"] = delta is not None and delta < 0
            row["groups"] = [name for name, members in (("model", model_set), ("postgres", pg_set)) if pid in members]
            current[identity] = row["cpu_seconds"]
            seen[identity] = dict(pid=pid, start_ticks=row["start_ticks"], uid=row["uid"], groups=row["groups"])
            rows.append(row)
        elapsed = (cycle_start - previous_time) / 1e9 if previous_time is not None else None
        group = {}
        for name, members, available in (("model", model_set, live), ("postgres", pg_set, pg["available"]),
            ("combined", model_set | pg_set, live and pg["available"])):
            group[name] = totals([row for row in rows if row["pid"] in members], available=available,
                discovery_complete=not errors, elapsed=elapsed)
            peak = peaks[name]
            if group[name]["pss_complete"]:
                pss = group[name]["pss_kib"]
                assert isinstance(pss, int)
                peak["pss"] = max(peak["pss"] or 0, pss)
            peak["rss"] = max(peak["rss"], group[name]["rss_sum_kib"])
            peak["threads"] = max(peak["threads"], group[name]["threads"])
            peak["cpu"] += group[name]["cpu_delta_seconds"]
            peak["incomplete"] += not group[name]["pss_complete"]
        if pg["available"]:
            pg_identities.add((pg["pid"], pg["start_ticks"]))
        first_ns = first_ns if first_ns is not None else cycle_start
        samples += 1
        emit(sys.stdout, dict(kind="sample", utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            cycle_start_ns=cycle_start, cycle_end_ns=time.monotonic_ns(),
            elapsed_since_launch_seconds=(cycle_start - launch_ns) / 1e9, interval_seconds=elapsed,
            collection_seconds=(time.monotonic_ns() - cycle_start) / 1e9, model_root_alive=live,
            model_root_identity=dict(pid=model_pid, start_ticks=expected_start, uid=expected_uid), postgres_root=pg,
            processes=rows, groups=group, overlapping_group_pids=sorted(model_set & pg_set),
            model_uid_violations=[row["pid"] for row in rows if "model" in row["groups"] and row["uid"] != expected_uid],
            disappeared_identities=[list(key) for key in previous.keys() - current.keys()], discovery_errors=errors))
        previous, previous_time = current, cycle_start
        if not live:
            break
        if args.max_seconds is not None and (time.monotonic_ns() - launch_ns) / 1e9 >= args.max_seconds:
            reason = "explicit_capture_window_limit"
            break
        time.sleep(max(0.0, args.interval - (time.monotonic_ns() - cycle_start) / 1e9))
    live_tail = [row for (pid, start), row in seen.items() if "model" in row["groups"] and pid in stats
        and stats[pid]["start_ticks"] == start and stats[pid]["state"] != "Z"]
    emit(sys.stdout, dict(kind="summary", reason=reason, samples=samples,
        first_sample_launch_gap_seconds=(first_ns - launch_ns) / 1e9 if first_ns is not None else None,
        capture_seconds=(time.monotonic_ns() - launch_ns) / 1e9,
        observed_peaks=peaks, postgres_root_identities=[list(value) for value in sorted(pg_identities)],
        observed_process_identities=list(seen.values()), observed_model_identities_still_live=live_tail,
        final_discovery_errors=errors, resource_qualification="not_established"))
    return 0


def controller(args, command):
    if os.geteuid() == 0:
        raise ValueError("controller/workload must run as normal user; sudo is observer-only")
    if command and Path(command[0]).name in {"sudo", "su", "runuser", "doas"}:
        raise ValueError("privilege-changing workload launch is outside this sampler contract")
    base = load_base()
    with args.out.open("x") as stream:
        emit(stream, dict(kind="metadata", capture_kind="wrapped_normal_user" if command else "attached_partial",
            controller_pid=os.getpid(), controller_uid=os.getuid(), controller_euid=os.geteuid(),
            interval_seconds=args.interval, command=command or None, pidfile=str(PG_PIDFILE),
            script_sha256=file_hash(Path(__file__)), base_sampler_sha256=file_hash(BASE),
            boot_id=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            clock_ticks_per_second=base.TICKS, memory_unit="KiB", sudo_reader=args.sudo_reader,
            limits="One sampled /proc discovery/collection window, not atomic. Short-lived/reparented/unreadable processes and CPU before first observation/after exit can be missed. PSS is proportional host sharing; RSS sums double-count shared pages. Whole PG cluster includes unrelated sessions. Controller/sudo/observer and other host workloads are excluded. No DB connection/service change or observed-tree signals."))
        observer_command = (["sudo", "-n", "--"] if args.sudo_reader else []) + ["/usr/bin/python3", "-B", str(Path(__file__).resolve()), "--reader", "--interval", str(args.interval)]
        if args.max_seconds is not None:
            observer_command += ["--max-seconds", str(args.max_seconds)]
        observer = child = None
        failure = None
        interrupted: BaseException | None = None
        summary_seen = False
        binding_sent = False
        discarded_packets = 0
        observer_code = command_code = command_exit_ns = None
        settlement_errors = []
        try:
            observer = subprocess.Popen(observer_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
            assert observer.stdin is not None and observer.stdout is not None
            if not select.select([observer.stdout], [], [], 15)[0]:
                raise TimeoutError("observer readiness timeout; no workload launched")
            line = observer.stdout.readline()
            if not line:
                raise RuntimeError("observer exited before readiness; no workload launched")
            ready = json.loads(line)
            emit(stream, ready)
            if (ready.get("kind") != "observer_ready" or ready.get("script_sha256") != file_hash(Path(__file__))
                or ready.get("base_sampler_sha256") != file_hash(BASE)
                or ready.get("observer_euid") != (0 if args.sudo_reader else os.geteuid())):
                raise ValueError("observer identity/source mismatch; no workload launched")
            if not ready.get("postgres_pss_readable") and not args.allow_partial_postgres:
                raise PermissionError("PostgreSQL PID/PSS unavailable; no workload launched")
            launch_ns = time.monotonic_ns()
            child = subprocess.Popen(command) if command else None
            pid = child.pid if child is not None else args.pid
            try:
                root = base.process_stat(pid)
                start = root["start_ticks"]
            except (OSError, ValueError, IndexError):
                start = None
            emit(stream, dict(kind="workload_launch" if child is not None else "workload_attach", pid=pid,
                start_ticks=start, uid=os.getuid(), launch_monotonic_ns=launch_ns, observer_ready_before_launch=True))
            emit(observer.stdin, dict(model_pid=pid, model_start_ticks=start, workload_uid=os.getuid(), launch_monotonic_ns=launch_ns))
            binding_sent = True
            for line in observer.stdout:
                packet = json.loads(line)
                if packet.get("kind") not in {"sample", "summary"}:
                    raise ValueError("unexpected observer packet after workload launch")
                summary_seen |= packet["kind"] == "summary"
                emit(stream, packet)
            if not summary_seen:
                raise RuntimeError("observer ended without capture summary")
        except BaseException as error:
            failure = dict(type=type(error).__name__, reason=str(error))
            interrupted = error if isinstance(error, (KeyboardInterrupt, SystemExit)) else None
        finally:
            # Never abandon a launched normal-user workload when capture fails.
            # Drain the observer while the command runs, so a full stdout pipe
            # cannot block its exit; failure is separate from command outcome.
            if observer is not None:
                try:
                    if observer.stdin is not None and not observer.stdin.closed:
                        if not binding_sent:
                            try:
                                emit(observer.stdin, {"abort": True})
                            except (OSError, ValueError):
                                pass
                        observer.stdin.close()
                except (OSError, ValueError) as error:
                    settlement_errors.append(dict(operation="observer_stdin_close", error=str(error)))
                try:
                    if observer.stdout is not None:
                        for line in observer.stdout:
                            try:
                                packet = json.loads(line)
                                summary_seen |= packet.get("kind") == "summary"
                                emit(stream, packet)
                            except (OSError, ValueError):
                                discarded_packets += 1
                        observer.stdout.close()
                except (OSError, ValueError) as error:
                    settlement_errors.append(dict(operation="observer_drain", error=str(error)))
                try:
                    observer_code = observer.wait()
                except BaseException as error:
                    settlement_errors.append(dict(operation="observer_wait", type=type(error).__name__, error=str(error)))
            if child is not None:
                try:
                    command_code = child.wait()
                    command_exit_ns = time.monotonic_ns()
                except BaseException as error:
                    settlement_errors.append(dict(operation="workload_wait", type=type(error).__name__, error=str(error)))
            final = dict(kind="controller_settlement", observer_pid=observer.pid if observer else None,
                observer_returncode=observer_code, workload_pid=child.pid if child else None,
                workload_returncode=command_code, workload_euid_at_launch=os.geteuid(),
                workload_exit_observed_monotonic_ns=command_exit_ns,
                capture_failure=failure, capture_summary_seen=summary_seen,
                discarded_observer_packets=discarded_packets, settlement_errors=settlement_errors,
                resource_qualification="not_established")
            try:
                emit(stream, final)
            except (OSError, ValueError):
                emit(sys.stderr, final)
            if child is not None and command_code is not None:
                exit_event = dict(kind="command_exit", returncode=command_code, pid=child.pid,
                    euid_at_launch=os.geteuid(), exit_observed_monotonic_ns=command_exit_ns)
                try:
                    emit(stream, exit_event)
                except (OSError, ValueError):
                    emit(sys.stderr, exit_event)
        if failure is not None and interrupted is not None:
            raise interrupted
        if failure is not None or settlement_errors or observer_code != 0:
            return command_code or 125
        return command_code or 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reader", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--sudo-reader", action="store_true")
    parser.add_argument("--allow-partial-postgres", action="store_true")
    parser.add_argument("--pid", type=int)
    parser.add_argument("--interval", type=float, default=.5)
    parser.add_argument("--max-seconds", type=float)
    parser.add_argument("--out", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not math.isfinite(args.interval) or args.interval <= 0 or (args.max_seconds is not None and (not math.isfinite(args.max_seconds) or args.max_seconds <= 0)):
        parser.error("sampling interval/window must be finite and positive")
    if args.reader:
        if command or args.pid or args.out:
            parser.error("read-only observer accepts no command or workload output path")
        return reader(args)
    if args.out is None or (args.pid is None) == (not command) or (args.pid is not None and args.pid < 1):
        parser.error("require output and exactly one normal-user command or attached PID")
    return controller(args, command)


if __name__ == "__main__":
    raise SystemExit(main())
