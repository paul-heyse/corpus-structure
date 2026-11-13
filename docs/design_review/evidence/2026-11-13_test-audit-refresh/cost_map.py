"""Aggregate stored `ci test` results into a cost map. Read-only; runs no tests.

Usage:
    python3 cost_map.py full <result-dir>          # one run in detail
    python3 cost_map.py narrowed <results-root> N  # fixed cost of the last N narrowed runs
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

PACKAGE_TESTS = "python/corpus-structure/tests/"
SUPERSEDED = (
    "semantic/test_operations.py",
    "semantic/test_runtime_bindings_native.py",
    "semantic/test_source_jit_native.py",
    "semantic/test_characterization_native.py",
    "orchestrate/test_characterization_recovery.py",
    "orchestrate/test_source_progress.py",
    "orchestrate/test_ready_coordination.py",
    "semantic/test_domain_operations.py",
)


def reports(result: Path):
    log = result / "ordinary" / "reportlog.jsonl"
    with log.open() as handle:
        for line in handle:
            if '"TestReport"' not in line:
                continue
            row = json.loads(line)
            if row.get("$report_type") == "TestReport":
                yield row


def load(path: Path):
    try:
        return json.loads(path.read_text())
    except OSError, ValueError:
        return None


def area(nodeid: str) -> str:
    path = nodeid.split("::", 1)[0]
    if path.startswith(PACKAGE_TESTS):
        rest = path[len(PACKAGE_TESTS) :]
        return "pkg/" + (rest.split("/", 1)[0] if "/" in rest else "(top)")
    return "root/" + "/".join(path.split("/")[:2])


def table(header: list[str], rows: list[list[object]]) -> None:
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join("---" for _ in header) + "|")
    for row in rows:
        print("| " + " | ".join(str(cell) for cell in row) + " |")
    print()


def full(result: Path) -> None:
    manifest = load(result / "manifest.json") or {}
    phase = defaultdict(float)
    by_area = defaultdict(lambda: defaultdict(float))
    by_file = defaultdict(lambda: defaultdict(float))
    by_test = defaultdict(lambda: defaultdict(float))
    worker = defaultdict(lambda: {"busy": 0.0, "first": None, "last": 0.0, "max_setup": 0.0})
    setups: list[float] = []
    for row in reports(result):
        when, duration, node = row["when"], row["duration"], row["nodeid"]
        phase[when] += duration
        by_area[area(node)][when] += duration
        by_file[node.split("::", 1)[0]][when] += duration
        by_test[node][when] += duration
        state = worker[row.get("worker_id", "main")]
        state["busy"] += duration
        state["first"] = row["start"] if state["first"] is None else min(state["first"], row["start"])
        state["last"] = max(state["last"], row["stop"])
        if when == "setup":
            setups.append(duration)
            state["max_setup"] = max(state["max_setup"], duration)

    total = sum(phase.values())
    start = min(state["first"] for state in worker.values())
    stop = max(state["last"] for state in worker.values())
    pytest_process = load(result / "ordinary" / "pytest.process.json") or {}
    print(f"## Run `{result.name}`\n")
    print(f"- scope: `{json.dumps(manifest.get('scope'))}`; counts: `{json.dumps((manifest.get('details') or {}).get('lane_counts'))}`")
    if manifest.get("settled"):
        print(f"- managed result wall time: {manifest['settled'] - manifest['started']:.0f} s")
    if pytest_process.get("finished"):
        print(f"- pytest process: {pytest_process['finished'] - pytest_process['started']:.0f} s; "
              f"process start to first test phase: {start - pytest_process['started']:.1f} s; "
              f"last test phase to process exit: {pytest_process['finished'] - stop:.1f} s")
    print(f"- test phases span {stop - start:.0f} s on {len(worker)} workers; summed phase time {total:.0f} worker-seconds "
          f"({total / ((stop - start) * len(worker)):.0%} of worker capacity over that span)")
    print(f"- tests: {len(by_test)}\n")

    table(["phase", "worker-seconds", "share"], [[k, f"{v:.0f}", f"{v / total:.0%}"] for k, v in sorted(phase.items(), key=lambda kv: -kv[1])])

    print("### Setup-duration distribution\n")
    rows = []
    for low, high in ((0, 0.05), (0.05, 0.3), (0.3, 1), (1, 2), (2, 5), (5, 15), (15, 1e9)):
        chosen = [s for s in setups if low <= s < high]
        rows.append([f"{low}–{high if high < 1e9 else '∞'} s", len(chosen), f"{sum(chosen):.0f}"])
    table(["setup time", "tests", "worker-seconds"], rows)

    print("### Workers\n")
    table(
        ["worker", "busy s", "largest single setup s", "first phase +s", "idle before end s"],
        [[name, f"{s['busy']:.0f}", f"{s['max_setup']:.1f}", f"{s['first'] - start:.1f}", f"{stop - s['last']:.0f}"]
         for name, s in sorted(worker.items(), key=lambda kv: int(re.sub(r"\D", "", kv[0]) or 0))],
    )

    print("### Areas\n")
    table(
        ["area", "setup", "call", "teardown", "total", "share"],
        [[name, f"{v['setup']:.0f}", f"{v['call']:.0f}", f"{v['teardown']:.0f}", f"{sum(v.values()):.0f}", f"{sum(v.values()) / total:.1%}"]
         for name, v in sorted(by_area.items(), key=lambda kv: -sum(kv[1].values()))[:16]],
    )

    counts = defaultdict(int)
    for node in by_test:
        counts[node.split("::", 1)[0]] += 1
    print("### Files by total worker-seconds (top 30)\n")
    table(
        ["file", "tests", "setup", "call", "teardown", "total", "setup+teardown per test"],
        [[name.replace(PACKAGE_TESTS, ""), counts[name], f"{v['setup']:.0f}", f"{v['call']:.0f}", f"{v['teardown']:.0f}",
          f"{sum(v.values()):.0f}", f"{(v['setup'] + v['teardown']) / counts[name]:.2f}"]
         for name, v in sorted(by_file.items(), key=lambda kv: -sum(kv[1].values()))[:30]],
    )

    print("### Tests by call time (top 20)\n")
    table(["test", "call s"], [[n.replace(PACKAGE_TESTS, ""), f"{v['call']:.0f}"] for n, v in sorted(by_test.items(), key=lambda kv: -kv[1]["call"])[:20]])

    families = defaultdict(lambda: defaultdict(float))
    cases = defaultdict(int)
    for node, value in by_test.items():
        name = node.split("[", 1)[0]
        cases[name] += 1
        for when, seconds in value.items():
            families[name][when] += seconds
    print("### Test functions by total worker-seconds, all cases (top 25)\n")
    table(
        ["test function", "cases", "setup", "call", "teardown"],
        [[n.replace(PACKAGE_TESTS, ""), cases[n], f"{v['setup']:.0f}", f"{v['call']:.0f}", f"{v['teardown']:.0f}"]
         for n, v in sorted(families.items(), key=lambda kv: -sum(kv[1].values()))[:25]],
    )

    def group(label: str, pick) -> list[object]:
        files = [name for name in by_file if pick(name)]
        sums = defaultdict(float)
        for name in files:
            for when, value in by_file[name].items():
                sums[when] += value
        tests = sum(counts[name] for name in files)
        subtotal = sum(sums.values())
        return [label, len(files), tests, f"{sums['setup']:.0f}", f"{sums['call']:.0f}", f"{sums['teardown']:.0f}", f"{subtotal:.0f}", f"{subtotal / total:.1%}"]

    print("### Selected groups\n")
    table(
        ["group", "files", "tests", "setup", "call", "teardown", "total", "share"],
        [
            group("`test_data_operation_*.py`", lambda n: "/test_data_operation_" in n),
            group("files tied to machinery the DDO plan removes", lambda n: n.endswith(SUPERSEDED)),
            group("`*_native.py`", lambda n: n.endswith("_native.py")),
            group("math", lambda n: "/tests/math/" in n),
            group("acceptance", lambda n: "/tests/acceptance/" in n),
        ],
    )


def narrowed(root: Path, limit: int) -> None:
    rows = []
    for manifest_path in sorted(root.glob("*/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        manifest = load(manifest_path)
        if not manifest or manifest.get("action") != "test" or not (manifest.get("scope") or {}).get("narrowed"):
            continue
        if manifest.get("outcome") != "passed" or not manifest.get("settled"):
            continue
        result = manifest_path.parent
        process = load(result / "ordinary" / "pytest.process.json")
        if not process or not process.get("finished"):
            continue
        busy, first, last, tests, setup = 0.0, None, 0.0, set(), 0.0
        try:
            for row in reports(result):
                busy += row["duration"]
                first = row["start"] if first is None else min(first, row["start"])
                last = max(last, row["stop"])
                tests.add(row["nodeid"])
                if row["when"] == "setup":
                    setup += row["duration"]
        except OSError:
            continue
        if first is None:
            continue
        workers = ((manifest["scope"].get("workers") or {}).get("ordinary") or {}).get("actual")
        rows.append({
            "id": result.name[:8], "tests": len(tests), "workers": workers,
            "wall": manifest["settled"] - manifest["started"],
            "before_pytest": process["started"] - manifest["started"],
            "to_first": first - process["started"],
            "span": last - first, "after": manifest["settled"] - last,
            "busy": busy, "setup": setup,
        })
        if len(rows) >= limit:
            break
    print(f"## Fixed cost of the last {len(rows)} passed narrowed runs\n")
    print("Columns: wall = managed result start to settle; pre = result start to pytest start; "
          "collect = pytest start to first test phase; span = first to last test phase; "
          "post = last test phase to settle; busy = summed phase time; setup = summed setup phases.\n")
    table(
        ["run", "tests", "workers", "wall", "pre", "collect", "span", "post", "busy", "setup"],
        [[r["id"], r["tests"], r["workers"], f"{r['wall']:.1f}", f"{r['before_pytest']:.1f}", f"{r['to_first']:.1f}",
          f"{r['span']:.1f}", f"{r['after']:.1f}", f"{r['busy']:.1f}", f"{r['setup']:.1f}"] for r in rows],
    )
    for key, label in (("wall", "wall"), ("to_first", "collect"), ("before_pytest", "pre"), ("after", "post"), ("span", "span")):
        values = [r[key] for r in rows]
        print(f"- {label}: median {statistics.median(values):.1f} s, min {min(values):.1f}, max {max(values):.1f}")
    fixed = [r["wall"] - r["span"] for r in rows]
    print(f"- wall minus test span: median {statistics.median(fixed):.1f} s, min {min(fixed):.1f}, max {max(fixed):.1f}")


if __name__ == "__main__":
    if sys.argv[1] == "full":
        full(Path(sys.argv[2]))
    else:
        narrowed(Path(sys.argv[2]), int(sys.argv[3]))
