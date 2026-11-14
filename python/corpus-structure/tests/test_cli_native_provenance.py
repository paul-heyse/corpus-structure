"""Retained native provenance gaps stay separate from actual pytest failure events."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from corpus_structure.cli.managed import ResultStore

REASON = "required native test has no complete item-bound acquisition context"


def retain(store: ResultStore, selections: dict[str, tuple[list[str], bool]]):
    with store.operation("test", scope={"required_lanes": list(selections)}) as result:
        for lane, (nodes, native) in selections.items():
            directory = result.directory / lane
            directory.mkdir()
            events = [
                {
                    "event": "collection_finish",
                    "selected": nodes,
                    "native_required": nodes if native else [],
                }
            ]
            reports: list[dict[str, object]] = [{"$report_type": "SessionStart"}]
            for node in nodes:
                events.extend(
                    [
                        {"event": "logstart", "nodeid": node},
                        {"event": "logfinish", "nodeid": node},
                    ]
                )
                for phase in ("setup", "call", "teardown"):
                    failed = not native and phase == "call"
                    reports.append(
                        {
                            "$report_type": "TestReport",
                            "nodeid": node,
                            "when": phase,
                            "outcome": "failed" if failed else "passed",
                            "longrepr": "AssertionError: actual call failure" if failed else None,
                        }
                    )
            code = int(not native)
            reports.append({"$report_type": "SessionFinish", "exitstatus": code})
            for filename, entries in (
                ("events-controller-1.jsonl", events),
                ("reportlog.jsonl", reports),
            ):
                (directory / filename).write_text(
                    "".join(json.dumps(row) + "\n" for row in entries)
                )
            (directory / "pytest.process.json").write_text(json.dumps({"returncode": code}))
            (directory / "invocation.json").write_text(json.dumps({"python_only": True}))
            result.publish(lane, directory)
        result.settle("failed", lanes={lane: "failed" for lane in selections})
    return result.id


def read(store, result_id, *args, json_output=True):
    return subprocess.run(
        [
            str(Path(sys.executable).with_name("ci")),
            "test",
            "failures",
            result_id,
            *args,
            *(["--json"] if json_output else []),
        ],
        cwd=Path(__file__).resolve().parents[3],
        env={**os.environ, "CORPUS_CI_RESULTS": str(store.root), "COLUMNS": "220"},
        capture_output=True,
        text=True,
        check=True,
    )


def test_installed_native_gap_pages_without_inventing_pytest_failures(tmp_path):
    store = ResultStore(tmp_path / "results")
    nodes = [f"tests/test_probe.py::test_native_{index}" for index in range(3)]
    result_id = retain(store, {"ordinary": (nodes, True)})
    report = json.loads(read(store, result_id, "--limit", "1").stdout)
    assert report["outcome"] == "failed"
    assert report["items"] == []
    assert report["available"] == 0
    gap = report["lanes"]["ordinary"]["native_provenance"]
    assert report["lanes"]["ordinary"]["native_observation"] == "incomplete"
    assert gap["reason"] == REASON
    assert gap["unresolved"] == nodes[:1]
    assert (gap["available"], gap["selected"], gap["omitted"], gap["next_after"]) == (3, 1, 2, 1)
    second = json.loads(
        read(
            store,
            result_id,
            "--lane",
            "ordinary",
            "--limit",
            "1",
            "--native-after",
            "1",
            "--phase",
            "call",
        ).stdout
    )
    assert second["items"] == []
    assert second["lanes"]["ordinary"]["native_provenance"]["unresolved"] == nodes[1:2]
    assert store.show(result_id).outcome == "failed"
    rendered = read(store, result_id, "--limit", "1", json_output=False).stdout
    assert REASON in rendered
    assert nodes[0] in rendered
    assert "--native-after 1" in rendered


def test_pytest_page_budget_does_not_hide_another_lanes_native_gap(tmp_path):
    store = ResultStore(tmp_path / "results")
    failed = "tests/test_probe.py::test_failed"
    unresolved = ["tests/test_probe.py::test_native_a", "tests/test_probe.py::test_native_b"]
    result_id = retain(store, {"ordinary": ([failed], False), "fault": (unresolved, True)})
    report = json.loads(read(store, result_id, "--limit", "1").stdout)
    assert [(item["lane"], item["phase"], item["nodeid"]) for item in report["items"]] == [
        ("ordinary", "call", failed),
    ]
    assert report["lanes"]["ordinary"]["native_provenance"] is None
    gap = report["lanes"]["fault"]["native_provenance"]
    assert gap["unresolved"] == unresolved[:1]
    assert gap["limit"] == 1
    assert gap["available"] == 2


def test_native_gap_identities_are_redacted_and_reason_bounds_are_explicit(tmp_path):
    store = ResultStore(tmp_path / "results")
    node = "tests/test_probe.py::test_native[password=fixture-native-secret]"
    result_id = retain(store, {"ordinary": ([node], True)})
    response = read(store, result_id, "--diagnostic-chars", "12")
    assert "fixture-native-secret" not in response.stdout
    gap = json.loads(response.stdout)["lanes"]["ordinary"]["native_provenance"]
    assert gap["sanitized_identities"] == 1
    assert gap["reason_truncated"]
    assert gap["reason"] == REASON[:12]
