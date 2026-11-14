"""Exercise bounded test reporting through installed ci and the receipt classifier."""

from __future__ import annotations

import errno
import fcntl
import json
import os
import pty
import re
import struct
import subprocess
import sys
import termios
from pathlib import Path

import pytest

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


def _receipt(
    directory: Path, nodes: list[str], *, fail: bool, invocation: dict | None = None
) -> None:
    directory.mkdir()
    events = [{"event": "collection_finish", "selected": nodes, "native_required": []}]
    reports: list[dict[str, object]] = [{"$report_type": "SessionStart"}]
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
                "longrepr": {
                    "reprcrash": {
                        "message": "AssertionError: password=fixture-secret " + "x" * 650
                    },
                    "reprtraceback": {"entries": ["must stay private"]},
                }
                if fail and phase == "call"
                else None,
            }
            for phase in ("setup", "call", "teardown")
        )
    code = int(fail)
    reports.append({"$report_type": "SessionFinish", "exitstatus": code})
    for name, stream in [("events-controller-12.jsonl", events), ("reportlog.jsonl", reports)]:
        (directory / name).write_text("".join(json.dumps(item) + "\n" for item in stream))
    (directory / "pytest.process.json").write_text(json.dumps({"returncode": code}))
    (directory / "invocation.json").write_text(
        json.dumps(invocation or {"source": {"head": "failed" if fail else "repaired"}})
    )


def test_installed_retry_retains_collection_failure_in_existing_failure_view(tmp_path):
    source = tmp_path / "test_broken_retry.py"
    source.write_text("def test_case(:\n    pass\n")
    node = source.as_posix() + "::test_case"
    store = ResultStore(tmp_path / "results")
    with store.operation("test", scope={"lane": "ordinary"}) as original:
        directory = original.directory / "ordinary"
        _receipt(directory, [node], fail=True)
        original.publish("ordinary", directory)
        original.settle("failed", lanes={"ordinary": "failed"})
    attempt = _run(store, "retry", original.id, "--lane", "ordinary", "--json", check=False)
    assert attempt.returncode == 1, attempt.stderr
    report = json.loads(attempt.stdout)
    assert report["outcome"] == "failed", report
    replacement = store.show(report["id"])
    assert replacement.details["execution_outcome"] == "not_run"
    assert replacement.details["retry_recollection_failed"]
    assert replacement.details["next_action"] == f"ci test retry {original.id}"
    assert "ordinary" in replacement.artifacts
    failures = json.loads(
        _run(store, "failures", report["id"], "--lane", "ordinary", "--json").stdout
    )
    assert failures["availability"] == "available"
    assert any("SyntaxError" in item.get("diagnostic", "") for item in failures["items"])
    assert failures["next_action"] == f"ci test retry {original.id}"


@pytest.mark.parametrize("retry", [False, True])
@pytest.mark.parametrize("workers", ["0", "-1", "1.5", "auto"])
def test_cli_workers_reject_invalid_before_operation(cli, tmp_path, retry, workers):
    arguments = ["test", *(["retry", "missing"] if retry else []), "--workers", workers]
    result = cli(*arguments, env={"CORPUS_CI_RESULTS": str(tmp_path / "results")})
    assert result.exit_code == 2, result.output
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("retry", [False, True])
def test_cli_fault_workers_reject_before_operation(cli, tmp_path, monkeypatch, retry):
    from corpus_structure.cli import testing

    def unexpected(*args, **kwargs):
        pytest.fail("fault worker refusal must precede validation, store access and execution")

    monkeypatch.setattr(testing, "_validate", unexpected)
    monkeypatch.setattr(testing, "result_store", unexpected)
    arguments = [
        "test",
        *(["retry", "missing"] if retry else []),
        "--lane",
        "fault",
        "--workers",
        "1",
        "--json",
    ]
    result = cli(*arguments, env={"CORPUS_CI_RESULTS": str(tmp_path / "results")})
    assert result.exit_code == 1, result.output
    assert "ordinary lane" in json.loads(result.stdout)["error"]["message"]
    assert not (tmp_path / "results").exists()


@pytest.mark.parametrize("retry", [False, True])
@pytest.mark.parametrize("workers", [None, 1])
@pytest.mark.parametrize("selection_count", [1, 3])
def test_cli_workers_reach_owned_recipe_and_scope(
    cli, tmp_path, monkeypatch, retry, workers, selection_count
):
    from corpus_structure.cli import testing

    store = ResultStore(tmp_path / "results")
    nodes = [f"tests/test_sample.py::test_{index}" for index in range(selection_count)]
    original_id = None
    if retry:
        with store.operation("test", scope={"lane": "ordinary"}) as original:
            directory = original.directory / "ordinary"
            _receipt(directory, nodes, fail=True)
            original.publish("ordinary", directory)
            original.settle("failed", lanes={"ordinary": "failed"})
            original_id = original.id
    monkeypatch.setenv("CORPUS_CI_TEST_WORKERS", "999")
    monkeypatch.setenv("PYTEST_XDIST_AUTO_NUM_WORKERS", "999")
    monkeypatch.setenv("CORPUS_CI_RUN_SCOPE", "qualification")
    calls = []
    collections = []

    def recipe(name, *args, env):
        assert name == "test-all"
        assert env.get("CORPUS_CI_TEST_WORKERS") == (str(workers) if workers else None)
        assert env["CORPUS_CI_PYTHON_ONLY"] == "1"
        assert env["CORPUS_CI_RUN_SCOPE"] == "narrowed"
        if retry:
            selection = Path(env["CORPUS_CI_SELECTION_FILE"])
            assert selection.read_text().splitlines() == nodes
        else:
            assert args == tuple(nodes)
        directory = Path(env["CORPUS_CI_RECEIPT_DIR"])
        directory.mkdir()
        (directory / "classification.json").write_text("{}")
        facts = {
            "requested": workers if workers is not None else 0 if selection_count == 1 else "auto",
            "actual": workers if workers is not None else 0 if selection_count == 1 else 2,
        }
        if workers is None and selection_count > 1:
            facts["maxprocesses"] = selection_count
        calls.append(facts)
        return subprocess.CompletedProcess(
            [],
            0,
            json.dumps(
                {
                    "counts": {"selected": selection_count, "passed": selection_count},
                    "workers": facts,
                    "custody_unsettled": False,
                    "retryable": False,
                    "status": "passed",
                    "empty": False,
                }
            ),
            "",
        )

    def supervisor(*args, **kwargs):
        if args == ("context",):
            return {}
        if "--write-unresolved" in args:
            collections.append(args)
            Path(args[args.index("--write-unresolved") + 1]).write_text("\n".join(nodes) + "\n")
        return {
            "custody_unsettled": False,
            "retryable": True,
            "required_unresolved": nodes,
            "contexts": [{"invocation": {}}],
        }

    monkeypatch.setattr(testing, "run_recipe", recipe)
    monkeypatch.setattr(testing, "_supervisor", supervisor)
    monkeypatch.setattr(testing, "_validate", lambda args: True)
    arguments = ["test", *(["retry", original_id, "--lane", "ordinary"] if retry else [])]
    if workers is not None:
        arguments += ["--workers", str(workers)]
    arguments += ["--json"]
    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState

    result = cli.runner.invoke(
        app,
        arguments,
        obj=CliState(test_args=() if retry else tuple(nodes)),
        env={"CORPUS_CI_RESULTS": str(store.root)},
    )
    assert result.exit_code == 0, result.output
    manifest = store.show(json.loads(result.stdout)["id"])
    assert manifest.scope["workers"] == {"ordinary": calls[0]}
    assert manifest.scope["required_lanes"] == ["ordinary"]
    assert len(collections) == int(retry)
    if retry:
        assert "--managed-selection" in collections[0]


@pytest.mark.parametrize("lane", ["ordinary", "fault"])
@pytest.mark.parametrize(
    "narrowed, retry, expected",
    [(False, False, "qualification"), (True, False, "narrowed"), (False, True, "narrowed")],
)
def test_lane_owns_run_scope_instead_of_inheriting_outer_value(
    tmp_path, monkeypatch, lane, narrowed, retry, expected
):
    from corpus_structure.cli import testing

    monkeypatch.setenv("CORPUS_CI_RUN_SCOPE", "outer-value")

    def recipe(name, *args, env):
        assert env["CORPUS_CI_RUN_SCOPE"] == expected
        directory = Path(env["CORPUS_CI_RECEIPT_DIR"])
        directory.mkdir()
        (directory / "classification.json").write_text("{}")
        return subprocess.CompletedProcess(
            [],
            0,
            json.dumps(
                {
                    "counts": {"selected": 1, "passed": 1},
                    "workers": {},
                    "custody_unsettled": False,
                    "retryable": False,
                    "status": "passed",
                    "empty": False,
                }
            ),
            "",
        )

    monkeypatch.setattr(testing, "run_recipe", recipe)
    with ResultStore(tmp_path / "results").operation("test", scope={}) as result:
        assert (
            testing._lane(
                result,
                lane,
                narrowed=narrowed,
                selection=tmp_path / "selection.txt" if retry else None,
            )
            == "passed"
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
    assert detail["next_actions"] == {original.id: f"ci test retry {original.id} --lane ordinary"}
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
        "diagnostic": ("AssertionError: password=********** " + "x" * 650)[:600],
        "diagnostic_truncated": True,
    }
    assert "fixture-secret" not in str(failure) and "must stay private" not in str(failure)
    assert failure["next_action"] == f"ci test retry {original.id} --lane ordinary"
    first = json.loads(_run(store, "failures", original.id, "--limit", "100", "--json").stdout)
    assert first["next_after"] == 100
    tail = json.loads(
        _run(store, "failures", original.id, "--after", "100", "--limit", "100", "--json").stdout
    )
    assert [item["nodeid"] for item in first["items"] + tail["items"]] == nodes
    assert tail["after"] == 100 and tail["next_after"] is None
    expanded = json.loads(
        _run(
            store,
            "failures",
            original.id,
            "--limit",
            "1",
            "--diagnostic-chars",
            "1024",
            "--json",
        ).stdout
    )
    assert expanded["items"][0]["diagnostic"] == "AssertionError: password=********** " + "x" * 650
    assert expanded["items"][0]["diagnostic_truncated"] is False
    assert "fixture-secret" not in str(expanded) and "must stay private" not in str(expanded)
    for invalid_bound in ("0", "32769"):
        assert (
            _run(
                store,
                "failures",
                original.id,
                "--diagnostic-chars",
                invalid_bound,
                check=False,
            ).returncode
            == 2
        )
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


def test_installed_failure_pagination_crosses_lanes_and_reports_worker_loss(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("test", scope={"lane": "all"}) as original:
        for name, count in (("ordinary", 3), ("fault", 4)):
            directory = original.directory / name
            _receipt(
                directory, [f"tests/test_{name}.py::test_{n}" for n in range(count)], fail=True
            )
            if name == "ordinary":
                (directory / "rust-state.json").write_text(
                    json.dumps(
                        dict(
                            status="not_run",
                            applicability="empty-selection",
                            listed_test_count=0,
                            functional_coverage=False,
                            reason="zero Rust tests establish no functional coverage",
                        )
                    )
                )
                with (directory / "events-controller-12.jsonl").open("a") as stream:
                    stream.write(
                        json.dumps(
                            dict(
                                event="worker_down",
                                lost_worker="gw2",
                                error="SIGKILL password=private",
                            )
                        )
                        + "\n"
                    )
            original.publish(name, directory)
        original.settle("failed", lanes={"ordinary": "failed", "fault": "failed"})
    page = json.loads(
        _run(store, "failures", original.id, "--after", "2", "--limit", "3", "--json").stdout
    )
    assert [(item["lane"], item["nodeid"].rsplit("::", 1)[1]) for item in page["items"]] == [
        ("ordinary", "test_2"),
        ("fault", "test_0"),
        ("fault", "test_1"),
    ]
    assert page["available"] == 7 and page["next_after"] == 5
    assert page["lanes"]["ordinary"]["reporting_errors"] == [
        "worker gw2: SIGKILL password=**********"
    ]
    assert not page["lanes"]["ordinary"]["reporting_complete"]
    assert page["lanes"]["ordinary"]["rust"]["listed_test_count"] == 0
    assert page["lanes"]["ordinary"]["rust"]["status"] == "not_run"
    assert not page["lanes"]["ordinary"]["rust"]["functional_coverage"]
    assert "private" not in json.dumps(page)
    clipped = json.loads(
        _run(store, "failures", original.id, "--diagnostic-chars", "20", "--json").stdout
    )
    assert clipped["lanes"]["ordinary"]["reporting_errors_truncated"]


def test_installed_failure_report_identifies_live_and_unsettled_custody(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("test", scope={"lane": "ordinary"}) as active:
        active.stage("ordinary")
        live = json.loads(_run(store, "failures", active.id, "--json").stdout)
        assert live["availability"] == "partial"
        assert live["lanes"]["ordinary"]["status"] == "running"
        assert live["next_action"] == f"ci results watch {active.id}"
        coverage = json.loads(
            _run(store, "coverage", active.id, "--view", "unresolved", "--json").stdout
        )
        assert coverage["active_attempts"] == [active.id]
        assert coverage["next_actions"] == {active.id: f"ci results watch {active.id}"}
        active.defer_settlement()
        active.settle("interrupted")
    retained = json.loads(_run(store, "failures", active.id, "--json").stdout)
    assert retained["availability"] == "unavailable"
    assert retained["next_action"] == f"ci results recover {active.id}"
    assert retained["items"] == []


def test_installed_coverage_distinguishes_context_changes_unknowns_and_receipt_custody(tmp_path):
    store = ResultStore(tmp_path)
    node = "tests/test_sample.py::test_case"
    source = {"head": "same"}
    with store.operation("test", scope={"lane": "ordinary"}) as original:
        lane = original.directory / "ordinary"
        _receipt(
            lane,
            [node],
            fail=True,
            invocation={"source": source, "python": "3.14.9", "versions": {"pytest": "9.0.1"}},
        )
        (lane / "pytest.process.json").write_text(
            json.dumps(
                {"returncode": 1, "owned_group_cleanup": {"group_present_after_cleanup": True}}
            )
        )
        original.publish("ordinary", lane)
        original.settle("failed")
    with store.operation("test.retry", scope={"lane": "ordinary"}) as repaired:
        lane = repaired.directory / "ordinary"
        _receipt(
            lane,
            [node],
            fail=False,
            invocation={"source": source, "python": "3.14.10", "versions": {"pytest": "9.0.2"}},
        )
        repaired.publish("ordinary", lane)
        repaired.settle("passed")
    coverage = json.loads(
        _run(store, "coverage", original.id, repaired.id, "--view", "unresolved", "--json").stdout
    )
    assert coverage["sources_differ"] is False
    assert coverage["context_differences"] == ["python", "pytest"]
    assert "pytest-xdist" in coverage["context_unknowns"]
    assert "source" not in coverage["context_unknowns"]
    assert coverage["status"] == "incomplete"
    assert coverage["unsettled_attempts"] == [original.id]
    assert list(coverage["next_actions"]) == [original.id]
    assert f"ci results show {original.id}" in coverage["next_actions"][original.id]
    refused = _run(store, "retry", original.id, "--lane", "ordinary", "--json", check=False)
    assert refused.returncode == 1
    assert "supervisor settlement unproven" in refused.stdout


def test_installed_failures_authenticate_only_selected_lane_and_refresh_retry_hint(tmp_path):
    store = ResultStore(tmp_path)
    node = "tests/test_sample.py::test_case"
    with store.operation("test", scope={"lane": "all"}) as result:
        for name in ("ordinary", "fault"):
            lane = result.directory / name
            _receipt(lane, [node], fail=True)
            result.publish(name, lane)
        result.settle(
            "failed",
            lanes={"ordinary": "failed", "fault": "failed"},
            next_action=f"ci test retry {result.id} --lane ordinary",
        )
    fault = result.directory / "fault"
    fault.rename(result.directory / "original-fault")
    _receipt(fault, [node], fail=True)
    ordinary = ("failures", result.id, "--lane", "ordinary", "--json")
    available = json.loads(_run(store, *ordinary).stdout)
    assert available["items"][0]["nodeid"] == node
    assert available["next_action"] == f"ci test retry {result.id} --lane ordinary"
    refused = _run(store, "failures", result.id, "--lane", "fault", "--json", check=False)
    assert refused.returncode == 1
    assert "differs from its owner publication" in refused.stdout
    all_lanes = _run(store, "failures", result.id, "--json", check=False)
    assert all_lanes.returncode == 1
    assert "differs from its owner publication" in all_lanes.stdout
    (result.directory / "ordinary" / "events-controller-12.jsonl").unlink()
    missing = json.loads(_run(store, *ordinary).stdout)
    assert missing["next_action"] == "ci test --lane ordinary"


def _terminal_stdout(store: ResultStore, width: int, *args: str) -> str:
    reader, terminal = pty.openpty()
    with os.fdopen(reader, "rb", buffering=0) as stream:
        try:
            fcntl.ioctl(terminal, termios.TIOCSWINSZ, struct.pack("HHHH", 24, width, 0, 0))
            env = {key: value for key, value in os.environ.items() if key != "COLUMNS"}
            done = subprocess.run(
                [str(Path(sys.executable).with_name("ci")), "test", *args],
                cwd=ROOT,
                env={**env, "CORPUS_CI_RESULTS": str(store.root), "TERM": "xterm", "NO_COLOR": "1"},
                stdout=terminal,
                stderr=subprocess.PIPE,
                timeout=15,
                check=True,
            )
        finally:
            os.close(terminal)
        data = bytearray()
        try:
            while chunk := stream.read(4096):
                data.extend(chunk)
        except OSError as error:
            if error.errno != errno.EIO:
                raise
    assert done.stderr == b""
    return data.decode()


@pytest.mark.parametrize("width", [44, 110])
def test_installed_named_reports_wrap_and_sanitize_the_same_ordered_identities(tmp_path, width):
    store = ResultStore(tmp_path)
    first = "tests/test_sample.py::test_alpha[字形[bold]]"
    raw = "tests/test_sample.py::test_beta[\x1b[91mtoken=fixture-secret&part=π]"
    second = "tests/test_sample.py::test_beta[token=**********&part=π]"
    with store.operation("test", scope={"lane": "ordinary"}) as result:
        lane = result.directory / "ordinary"
        _receipt(lane, [raw, first], fail=True)
        result.publish("ordinary", lane)
        result.settle("failed")
    for args, ordering, column in (
        (("failures", result.id), "lane_collection_node_phase", 2),
        (("coverage", result.id, "--view", "unresolved"), "node_id", 1),
    ):
        machine = json.loads(_run(store, *args, "--json").stdout)
        assert machine["ordering"] == ordering
        assert machine["sanitized_identities"] == 1
        assert [item["nodeid"] for item in machine["items"]] == [first, second]
        human = _terminal_stdout(store, width, *args)
        assert "Order" in human
        assert "fixture-secret" not in human and "\x1b[91m" not in human
        plain = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", human)
        displayed = "".join(
            line.split("│")[column].strip() for line in plain.splitlines() if line.startswith("│")
        )
        assert first + second in displayed


def test_installed_native_traceback_projects_locations_chain_and_redacts_before_bounds(tmp_path):
    store = ResultStore(tmp_path)
    node = "tests/test_example.py::test_example"
    native = {
        "reprcrash": {
            "path": "raised.py",
            "lineno": 31,
            "message": "AssertionError: password=fixture-secret",
        },
        "reprtraceback": {
            "reprentries": [
                {
                    "type": "ReprEntry",
                    "data": {
                        "reprfileloc": {
                            "path": "native_helper.py",
                            "lineno": 17,
                            "message": "helper location password=location-secret",
                        },
                        "lines": ["SOURCE-PRIVATE"],
                        "reprlocals": {"lines": ["LOCALS-PRIVATE"]},
                        "reprfuncargs": {"args": [["name", "ARGS-PRIVATE"]]},
                    },
                }
            ]
        },
        "chain": [
            [
                {"reprentries": []},
                {"path": "cause.py", "lineno": 7, "message": "token=cause-secret"},
                "native description password=description-secret",
            ]
        ],
        "sections": [["Captured stdout", "STREAM-PRIVATE"]],
    }
    with store.operation("test", scope={"lane": "ordinary"}) as result:
        directory = result.directory / "ordinary"
        _receipt(directory, [node], fail=True)
        reportlog = directory / "reportlog.jsonl"
        reports = [json.loads(line) for line in reportlog.read_text().splitlines()]
        for report in reports:
            if report.get("outcome") == "failed":
                report["longrepr"] = native
        reportlog.write_text("".join(json.dumps(report) + "\n" for report in reports))
        result.publish("ordinary", directory)
        result.settle("failed", lanes={"ordinary": "failed"})
    default = json.loads(_run(store, "failures", result.id, "--json").stdout)
    assert "native_traceback" not in default["items"][0]
    args = ("failures", result.id, "--native-traceback", "--diagnostic-chars", "4096")
    response = _run(store, *args, "--json")
    projected = json.loads(response.stdout)["items"][0]["native_traceback"]
    assert projected["availability"] == "available"
    assert projected["locations"][1] == {
        "native_path": "$.longrepr.reprtraceback.reprentries[0].data.reprfileloc",
        "role": "reprfileloc",
        "path": "native_helper.py",
        "lineno": 17,
        "message": "helper location password=**********",
    }
    assert projected["chains"][0]["description"] == "native description password=**********"
    assert not any(
        word in response.stdout
        for word in (
            "fixture-secret",
            "location-secret",
            "cause-secret",
            "description-secret",
            "SOURCE-PRIVATE",
            "LOCALS-PRIVATE",
            "ARGS-PRIVATE",
            "STREAM-PRIVATE",
        )
    )
    human = _run(store, *args).stdout
    assert "Native pytest locations" in human and "native_helper.py" in human and "17" in human
    clipped = json.loads(
        _run(
            store, "failures", result.id, "--native-traceback", "--diagnostic-chars", "20", "--json"
        ).stdout
    )["items"][0]["native_traceback"]
    assert clipped["availability"] == "partial" and clipped["omissions"]
    assert "secret" not in json.dumps(clipped)
    assert (
        sum(
            len(location[key] or "")
            for location in clipped["locations"]
            for key in ("path", "message")
        )
        + sum(len(chain["description"] or "") for chain in clipped["chains"])
        <= 20
    )


def test_installed_native_traceback_marks_rendered_only_format_unavailable(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("test", scope={"lane": "ordinary"}) as result:
        directory = result.directory / "ordinary"
        _receipt(directory, ["tests/test_example.py::test_example"], fail=True)
        reportlog = directory / "reportlog.jsonl"
        reports = [json.loads(line) for line in reportlog.read_text().splitlines()]
        for report in reports:
            if report.get("outcome") == "failed":
                report["longrepr"] = "ValueError: original rendered summary"
        reportlog.write_text("".join(json.dumps(report) + "\n" for report in reports))
        result.publish("ordinary", directory)
        result.settle("failed", lanes={"ordinary": "failed"})
    response = json.loads(_run(store, "failures", result.id, "--native-traceback", "--json").stdout)
    item = response["items"][0]
    assert item["diagnostic"] == "ValueError: original rendered summary"
    assert item["native_traceback"]["availability"] == "unavailable"
    assert item["native_traceback"]["omissions"][0]["native_path"] == "$.longrepr"


def test_observation_journal_is_ancillary_to_test_receipts_coverage_and_retry(tmp_path, cli):
    from contextlib import ExitStack

    from corpus_structure.cli import testing

    store = ResultStore(tmp_path)
    node = "tests/test_sample.py::test_observed_case"
    # Use the real owner/writer/publication lifecycle and exercise the legacy scope
    # fallback as well as installed report consumers of the same retained result.
    with store.operation("test", observations=True) as original:
        lane = original.directory / "ordinary"
        _receipt(lane, [node], fail=False)
        original.publish("ordinary", lane)
        original.settle("passed")
    manifest = store.show(original.id)
    assert set(manifest.artifacts) == {"ordinary", "observations"}
    with ExitStack() as leases:
        assert set(testing._receipts(store, manifest, leases)) == {"ordinary"}
    assert testing._required_lanes(manifest) == {"ordinary"}
    full = json.loads(_run(store, "coverage", original.id, "--json").stdout)
    assert full["node_coverage"]["required"] == [node]
    assert full["node_coverage"]["unresolved"] == []
    assert full["missing_lanes"] == []
    summary = json.loads(
        _run(
            store, "coverage", original.id, "--view", "unresolved", "--limit", "1", "--json"
        ).stdout
    )
    assert {
        key: summary["node_coverage"][key] for key in ("required", "covered", "unresolved")
    } == {"required": 1, "covered": 1, "unresolved": 0}
    assert summary["selected_lanes"] == ["ordinary"]
    assert set(full["lane_selections"]) == {"ordinary"}
    assert summary["missing_lanes"] == [] and summary["status"] == "passed"
    report = json.loads(_run(store, "failures", original.id, "--json").stdout)
    assert set(report["lanes"]) == {"ordinary"} and report["items"] == []
    retry = _run(store, "retry", original.id, "--json", check=False)
    assert retry.returncode == 1
    assert json.loads(retry.stdout)["error"]["message"] == "no unresolved test selection"
    (attempt,) = store.list(None, 10, "test.retry").results
    assert attempt.scope["required_lanes"] == []
    assert set(attempt.artifacts) == {"observations"}
    exported = cli(
        "results",
        "export",
        original.id,
        "--role",
        "observations",
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert exported.exit_code == 0, exported.output
    assert Path(json.loads(exported.stdout)["path"]) == original.directory / "observations.jsonl"
    journal = store.read_observations(original.id)
    assert journal.standing == "sealed" and journal.authentication_bytes > 0
    assert {item.kind for item in journal.rows} == {"invocation", "settlement"}
    assert store.deliver(original.id, None, None) == lane
