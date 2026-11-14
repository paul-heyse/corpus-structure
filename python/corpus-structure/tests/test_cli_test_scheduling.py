"""Bounded installed views for collection affinity, observed workers and child startup failure."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from corpus_structure.cli.managed import ResultStore


def invoke(store, *args):
    return subprocess.run(
        [str(Path(sys.executable).with_name("ci")), "test", *args],
        env={**os.environ, "CORPUS_CI_RESULTS": str(store.root)},
        capture_output=True,
        text=True,
        check=True,
    )


def write_stream(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_installed_scheduling_pages_logical_members_and_reports_observed_workers(tmp_path):
    store = ResultStore(tmp_path / "results")
    nodes = [f"tests/test_affinity.py::test_case_{index}" for index in range(3)]
    scheduled = [node + "@preparation" for node in nodes]
    with store.operation("test", scope={"lane": "ordinary"}) as result:
        directory = result.directory / "ordinary"
        directory.mkdir()
        write_stream(
            directory / "events-gw1-12.jsonl",
            [
                {
                    "event": "collection_finish",
                    "selected": scheduled,
                    "native_required": [],
                    "nodeid_aliases": dict(zip(scheduled, nodes, strict=True)),
                    "affinity_groups": {node: ["preparation"] for node in scheduled},
                },
                *[
                    {"event": "phase_start", "nodeid": node, "worker": "gw1", "phase": "call"}
                    for node in scheduled[:2]
                ],
                {
                    "event": "native_context",
                    "scope": "session",
                    "worker": "gw1",
                    "pid": 12,
                    "context": {
                        "native_test_deployment": {
                            "head": "cs_sem_head_" + "a" * 16,
                            "key": "a" * 64,
                            "run_scope": "narrowed",
                            "acquisition": "reused",
                            "verification": "verified",
                            "deployment_key_gap": None,
                        }
                    },
                },
            ],
        )
        write_stream(
            directory / "reportlog.jsonl",
            [{"$report_type": "SessionStart"}, {"$report_type": "SessionFinish", "exitstatus": 0}],
        )
        (directory / "pytest.process.json").write_text('{"returncode":0}')
        (directory / "invocation.json").write_text(
            json.dumps({"workers": {"requested": "auto", "maxprocesses": 2, "actual": 2}})
        )
        result.publish("ordinary", directory)
        result.settle("failed", lanes={"ordinary": "failed"})
        result_id = result.id
    first = json.loads(
        invoke(
            store, "scheduling", result_id, "--group", "preparation", "--limit", "1", "--json"
        ).stdout
    )
    assert first["available"] == 3 and first["selected"] == 1 and first["next_after"] == 1
    assert first["items"] == [
        {
            "lane": "ordinary",
            "nodeid": nodes[0],
            "affinity_groups": ["preparation"],
            "observed_workers": ["gw1"],
            "scheduled_workers": None,
            "native_required": False,
        }
    ]
    lane = first["lanes"]["ordinary"]
    assert lane["group_metadata_complete"]
    assert lane["workers"] == {"requested": "auto", "maxprocesses": 2, "actual": 2}
    assert lane["deployments"][0]["worker"] == "gw1"
    assert lane["deployments"][0]["verification"] == "verified"
    last = json.loads(invoke(store, "scheduling", result_id, "--after", "2", "--json").stdout)
    assert last["items"][0]["nodeid"] == nodes[2]
    assert last["items"][0]["observed_workers"] == []
    assert last["items"][0]["scheduled_workers"] is None


@pytest.mark.parametrize("oversized", [False, True])
def test_installed_startup_failure_has_bounded_redacted_diagnostic_without_fake_nodes(
    tmp_path, oversized
):
    store = ResultStore(tmp_path / "results")
    with store.operation("test", scope={"lane": "ordinary"}) as result:
        directory = result.directory / "ordinary"
        directory.mkdir()
        (directory / "reportlog.jsonl").write_text("")
        (directory / "pytest.process.json").write_text('{"returncode":4}')
        (directory / "pytest.stderr").write_text(
            "source_listing = 'must stay private'\n"
            "E   ImportError: cannot import SemanticTemplate password=fixture-secret\n"
            + ("x" * 66000 if oversized else "")
        )
        result.publish("ordinary", directory)
        result.settle("failed", lanes={"ordinary": "failed"})
        result_id = result.id
    response = invoke(store, "failures", result_id, "--native-traceback", "--json")
    report = json.loads(response.stdout)
    assert report["selected"] == report["available"] == 0
    assert report["items"] == []
    startup = report["lanes"]["ordinary"]["startup"]
    assert startup["kind"] == "pytest_child_startup"
    assert startup["source"] == "pytest.stderr"
    assert startup["availability"] == ("omitted" if oversized else "available")
    assert "fixture-secret" not in response.stdout
    assert "must stay private" not in response.stdout
    if not oversized:
        assert "ImportError" in startup["diagnostic"]
        assert "SemanticTemplate" in startup["diagnostic"]
