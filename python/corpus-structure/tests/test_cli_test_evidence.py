"""Exercise bounded test reporting through installed ci and the receipt classifier."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from corpus_structure.cli.managed import ResultStore

ROOT = Path(__file__).resolve().parents[3]


def _run(store: ResultStore, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(Path(sys.executable).with_name("ci")), "test", *args],
        cwd=ROOT,
        env={**os.environ, "CORPUS_CI_RESULTS": str(store.root), "COLUMNS": "44"},
        capture_output=True,
        text=True,
        check=check,
    )


def _receipt(directory: Path, nodes: list[str], *, fail: bool) -> None:
    directory.mkdir()
    events = [{"event": "collection_finish", "selected": nodes, "native_required": []}]
    reports: list[dict[str, str | int]] = [{"$report_type": "SessionStart"}]
    for node in nodes:
        events.extend(
            [
                {"event": "logstart", "nodeid": node},
                {"event": "logfinish", "nodeid": node},
            ]
        )
        reports.extend(
            {
                "$report_type": "TestReport",
                "nodeid": node,
                "when": phase,
                "outcome": "failed" if fail and phase == "call" else "passed",
            }
            for phase in ("setup", "call", "teardown")
        )
    code = int(fail)
    reports.append({"$report_type": "SessionFinish", "exitstatus": code})
    for name, stream in [("events-controller-12.jsonl", events), ("reportlog.jsonl", reports)]:
        (directory / name).write_text("".join(json.dumps(item) + "\n" for item in stream))
    (directory / "pytest.process.json").write_text(json.dumps({"returncode": code}))
    (directory / "invocation.json").write_text(
        json.dumps({"source": {"head": "failed" if fail else "repaired"}})
    )


def test_installed_compact_coverage_and_exact_failures(tmp_path):
    store = ResultStore(tmp_path)
    nodes = [f"tests/test_sample.py::test_case_{index:03}" for index in range(103)]
    with store.operation("test", scope={"lane": "all"}) as original:
        lane = original.directory / "ordinary"
        _receipt(lane, nodes, fail=True)
        original.publish("ordinary", lane)
        original.settle("failed", lanes={"ordinary": "failed", "fault": "failed"})
    with store.operation("test.retry", scope={"lane": "ordinary"}) as repaired:
        lane = repaired.directory / "ordinary"
        _receipt(lane, nodes, fail=False)
        repaired.publish("ordinary", lane)
        repaired.settle("passed")

    detail = json.loads(
        _run(
            store, "coverage", original.id, "--view", "unresolved", "--limit", "3", "--json"
        ).stdout
    )
    assert detail["node_coverage"]["required"] == 103
    assert detail["node_coverage"]["covered"] == 0
    assert detail["missing_lanes"] == ["fault"]
    assert detail["attempt_outcomes"] == {original.id: "failed"}
    assert (detail["available"], detail["selected"], detail["omitted"]) == (103, 3, 100)
    assert [item["nodeid"] for item in detail["items"]] == nodes[:3]
    assert detail["items"][0]["observations"] == ["failed"]
    raw = subprocess.run(
        [
            sys.executable,
            "scripts/test_receipts.py",
            "classify",
            "--projection",
            "coverage",
            "--receipt-dir",
            str(original.directory / "ordinary"),
            "--required-lane",
            "ordinary",
            "--required-lane-from",
            "ordinary",
            str(original.directory / "ordinary"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert raw.returncode == 1  # The classified original attempt failed.
    projection = json.loads(raw.stdout)
    assert projection["node_coverage"]["required"] == 103
    assert "contexts" not in projection and "items" not in projection
    assert not any(node in raw.stdout for node in nodes)

    full = json.loads(_run(store, "coverage", original.id, repaired.id, "--json").stdout)
    assert full["node_coverage"]["required"] == nodes
    assert full["node_coverage"]["unresolved"] == []
    assert full["missing_lanes"] == ["fault"]
    assert full["sources_differ"] is True
    human = _run(store, "coverage", original.id, repaired.id).stdout
    assert "103/103 covered" in human and "failed" in human and "fault" in human
    assert "Sources differ" in human and not any(node in human for node in nodes)

    failure = json.loads(
        _run(store, "failures", original.id, "--phase", "call", "--limit", "2", "--json").stdout
    )
    assert failure["availability"] == "partial"  # The declared fault lane has no receipt.
    assert (failure["available"], failure["selected"], failure["omitted"]) == (103, 2, 101)
    assert failure["items"][0] == {
        "lane": "ordinary",
        "nodeid": nodes[0],
        "phase": "call",
        "outcome": "failed",
        "reason": "pytest_failure",
    }
    assert failure["next_action"] == f"ci test retry {original.id} --lane ordinary"
    filtered = json.loads(
        _run(
            store, "failures", original.id, "--lane", "ordinary", "--phase", "teardown", "--json"
        ).stdout
    )
    assert filtered["availability"] == "available"
    assert filtered["items"] == []
    bad = _run(
        store, "coverage", original.id, "--view", "unresolved", "--limit", "101", check=False
    )
    assert bad.returncode == 2


def test_installed_failure_report_identifies_live_and_unsettled_custody(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("test", scope={"lane": "ordinary"}) as active:
        active.stage("ordinary")
        live = json.loads(_run(store, "failures", active.id, "--json").stdout)
        assert live["availability"] == "partial"
        assert live["lanes"]["ordinary"]["status"] == "running"
        assert live["next_action"] == f"ci results watch {active.id}"
        active.defer_settlement()
        active.settle("interrupted")
    retained = json.loads(_run(store, "failures", active.id, "--json").stdout)
    assert retained["availability"] == "unavailable"
    assert retained["next_action"] == f"ci results recover {active.id}"
    assert retained["items"] == []
