"""Bounded read-only host/process/GPU observations for one managed invocation.

No database access, model execution, environment capture or process command lines.
Host-wide observations and observed descendant attribution remain distinct.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

STOP = None


def stop(signum, _frame):
    global STOP
    STOP = signal.Signals(signum).name


def now():
    return datetime.now(timezone.utc).isoformat()


def managed(directory):
    try:
        value = json.loads((directory / 'manifest.json').read_bytes())
        return {k: value.get(k) for k in ('id', 'action', 'stage', 'outcome', 'started', 'settled')} | {'custody_unsettled': value.get('details', {}).get('custody_unsettled')}
    except (OSError, ValueError) as error:
        return {'availability': 'unavailable', 'reason': type(error).__name__}


def producer_pid(directory):
    try:
        with (directory / 'observations.jsonl').open() as stream:
            for _ in range(10):
                line = stream.readline(65537)
                if not line or len(line) > 65536:
                    break
                producer = json.loads(line).get('producer', '')
                if producer.startswith('process:'):
                    return int(producer.split(':')[1])
    except (OSError, ValueError, IndexError):
        pass
    return None


def processes():
    values = {}
    denied = vanished = 0
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            raw = (path / 'stat').read_text()
            end = raw.rindex(')')
            fields = raw[end + 2:].split()
            pid = int(path.name)
            values[pid] = dict(pid=pid, name=raw[raw.index('(') + 1:end], state=fields[0], ppid=int(fields[1]), start_ticks=int(fields[19]), cpu_ticks=int(fields[11]) + int(fields[12]), rss_bytes=int(fields[21]) * os.sysconf('SC_PAGE_SIZE'), virtual_bytes=int(fields[20]))
        except PermissionError:
            denied += 1
        except (OSError, ValueError, IndexError):
            vanished += 1
    return values, {'permission_denied': denied, 'vanished_or_unreadable': vanished}


def host(previous):
    memory = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, rest = line.split(':', 1)
        if key in {'MemTotal', 'MemAvailable', 'MemFree', 'Cached', 'Buffers', 'SwapTotal', 'SwapFree'}:
            memory[key + '_bytes'] = int(rest.split()[0]) * 1024
    fields = [int(v) for v in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    counters = (sum(fields), fields[3] + fields[4])
    busy = None
    if previous and counters[0] > previous[0]:
        busy = 100 * (1 - (counters[1] - previous[1]) / (counters[0] - previous[0]))
    return {'cpu_busy_percent_interval': busy, 'load_average': list(os.getloadavg()), 'memory': memory}, counters


def query_gpu(fields, kind='gpu'):
    command = ['nvidia-smi', '--query-' + kind + '=' + ','.join(fields), '--format=csv,noheader,nounits']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
        if result.returncode:
            return {'availability': 'unavailable', 'reason': 'nvidia-smi exit', 'exit_code': result.returncode}
        return {'availability': 'available', 'rows': [dict(zip(fields, (item.strip() for item in row), strict=True)) for row in csv.reader(result.stdout.splitlines()) if row]}
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        return {'availability': 'unavailable', 'reason': type(error).__name__}


def positive(value):
    number = float(value)
    if not 0 < number <= 86400:
        raise argparse.ArgumentTypeError('requires a positive bound at most86400 seconds')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--results-root', type=Path, default=Path('build/ci'))
    parser.add_argument('--root-pid', type=int)
    parser.add_argument('--interval', type=positive, default=5)
    parser.add_argument('--max-seconds', type=positive, default=3600)
    args = parser.parse_args()
    if len(args.result) != 32 or any(c not in '0123456789abcdef' for c in args.result):
        parser.error('result must be an exact managed32hex ID')
    if args.root_pid is not None and args.root_pid <= 0:
        parser.error('root PID must be positive')
    directory = args.results_root.resolve() / args.result
    if not (directory / 'manifest.json').is_file():
        parser.error('managed manifest unavailable')
    root_pid = args.root_pid or producer_pid(directory)
    initial, _errors = processes()
    root_identity = (root_pid, initial[root_pid]['start_ticks']) if root_pid in initial else None
    tracked = {root_identity} if root_identity else set()
    previous_processes, previous_host, previous_time = {}, None, None
    start = time.monotonic()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, stop)
    with args.output.open('x') as stream:
        def write(value):
            stream.write(json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n')
            stream.flush()
        write(dict(kind='header', timestamp=now(), result_id=args.result, command=[sys.executable, *sys.argv], helper_sha256=sha256(Path(__file__).read_bytes()).hexdigest(), python=sys.version, kernel=os.uname().release, boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), cpu_count=os.cpu_count(), clock_ticks_per_second=os.sysconf('SC_CLK_TCK'), interval_seconds=args.interval, maximum_seconds=args.max_seconds, root_identity={'pid': root_identity[0], 'start_ticks': root_identity[1]} if root_identity else None, attribution='Host CPU/RAM/GPU counters are host-wide. Owned means currently observed process-tree membership anchored by stable PID/start_ticks; detached prior children may be missed. RSS sum can double-count shared pages. GPU utilization/power cannot be attributed to this invocation. No command lines or environment are collected.'))
        print(json.dumps({'sampler_pid': os.getpid(), 'result_id': args.result, 'output': str(args.output.resolve()), 'root_identity': root_identity}), flush=True)
        samples = 0
        reason = 'duration_bound'
        while time.monotonic() - start < args.max_seconds and STOP is None:
            snapshot_start = time.monotonic()
            current, process_errors = processes()
            selected = {pid for pid, row in current.items() if (pid, row['start_ticks']) in tracked}
            changed = True
            while changed:
                additions = {pid for pid, row in current.items() if row['ppid'] in selected} - selected
                changed = bool(additions)
                selected.update(additions)
            tracked.update((pid, current[pid]['start_ticks']) for pid in selected)
            elapsed = snapshot_start - previous_time if previous_time is not None else None
            owned = []
            for pid in sorted(selected):
                row = current[pid].copy()
                identity = (pid, row['start_ticks'])
                prior = previous_processes.get(identity)
                row['cpu_percent_interval_one_core_units'] = 100 * (row['cpu_ticks'] - prior) / os.sysconf('SC_CLK_TCK') / elapsed if prior is not None and elapsed else None
                owned.append(row)
            host_state, previous_host = host(previous_host)
            gpu = query_gpu(['uuid', 'name', 'utilization.gpu', 'utilization.memory', 'memory.total', 'memory.used', 'power.draw', 'power.limit', 'temperature.gpu'])
            gpu_processes = query_gpu(['gpu_uuid', 'pid', 'used_gpu_memory'], 'compute-apps')
            for row in gpu_processes.get('rows', []):
                pid = int(row['pid']) if row['pid'].isdecimal() else None
                row['observed_owned_descendant'] = pid in selected
                row['start_ticks'] = current[pid]['start_ticks'] if pid in current else None
            state = managed(directory)
            write(dict(kind='sample', timestamp=now(), monotonic_seconds_since_start=snapshot_start-start, result=state, host=host_state, owned_processes=owned, owned_rss_sum_bytes=sum(r['rss_bytes'] for r in owned), process_observation_errors=process_errors, gpu_hostwide=gpu, gpu_compute_processes=gpu_processes, snapshot_duration_seconds=time.monotonic()-snapshot_start))
            samples += 1
            previous_processes = {(pid, row['start_ticks']): row['cpu_ticks'] for pid, row in current.items() if pid in selected}
            previous_time = snapshot_start
            if state.get('settled') is not None:
                reason = 'managed_invocation_settled'
                break
            delay = min(args.interval, args.max_seconds - (time.monotonic()-start))
            until = time.monotonic() + max(0, delay)
            while STOP is None and time.monotonic() < until:
                time.sleep(min(0.25, max(0, until-time.monotonic())))
        write(dict(kind='end', timestamp=now(), reason=STOP or reason, samples=samples, result=managed(directory), elapsed_seconds=time.monotonic()-start))


if __name__ == '__main__':
    main()
