"""Independent event fixtures and bounded real child processes for qualification reporting."""

from __future__ import annotations

import io
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import uuid
from contextlib import suppress
from pathlib import Path

import pytest

from test_receipts import (
    _complete_native_context,
    classify,
    classify_receipt,
    classify_rust,
    run_process,
    run_python,
)


def stream(path: Path, events: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(event) + "\n" for event in events))


def receipt(
    tmp_path: Path,
    reports: list[dict[str, object]],
    *,
    finish: bool = True,
    selected: tuple[str, ...] = ("a", "b"),
    returncode: int = 0,
) -> Path:
    events: list[dict[str, object]] = [{"$report_type": "SessionStart"}, *reports]
    if finish:
        events.append({"$report_type": "SessionFinish", "exitstatus": returncode})
    stream(tmp_path / "reportlog.jsonl", events)
    stream(
        tmp_path / "events-controller-12.jsonl",
        [
            {"event": "collection_finish", "selected": selected, "pid": 12, "worker": "controller"},
            {"event": "logstart", "nodeid": "a", "pid": 12, "worker": "controller"},
            {"event": "logfinish", "nodeid": "a", "pid": 12, "worker": "controller"},
        ],
    )
    (tmp_path / "pytest.process.json").write_text(json.dumps({"returncode": returncode}))
    return tmp_path


def report(phase: str, outcome: str = "passed", **extra: object) -> dict[str, object]:
    return {"$report_type": "TestReport", "nodeid": "a", "when": phase, "outcome": outcome, **extra}


def test_teardown_failure_overrides_call_and_keeps_unstarted(tmp_path: Path) -> None:
    result = classify_receipt(
        receipt(
            tmp_path, [report("setup"), report("call"), report("teardown", "failed")], returncode=1
        )
    )
    assert result["status"] == "failed"
    assert result["nodes"]["a"]["status"] == "failed"
    assert result["nodes"]["b"]["status"] == "not_run"
    assert len(result["nodes"]["a"]["reports"]) == 3


def test_missing_finish_keeps_completed_pass(tmp_path: Path) -> None:
    result = classify_receipt(
        receipt(
            tmp_path,
            [report("setup"), report("call"), report("teardown")],
            finish=False,
            returncode=-9,
        )
    )
    assert result["status"] == "incomplete"
    assert result["process_failed"]
    assert result["nodes"]["a"]["status"] == "passed"
    assert result["nodes"]["b"]["status"] == "not_run"


@pytest.mark.parametrize("optional,expected", [(False, "blocked"), (True, "inapplicable")])
def test_skip_requires_explicit_applicability(
    tmp_path: Path, optional: bool, expected: str
) -> None:
    properties = [("qualification_reason", "provider is absent")]
    if optional:
        properties.append(("qualification_optional", "outside selected scope"))
    result = classify_receipt(
        receipt(tmp_path, [report("setup", "skipped", user_properties=properties)], selected=("a",))
    )
    assert result["nodes"]["a"]["status"] == expected
    assert result["nodes"]["a"]["reason"] == "provider is absent"


def test_prerequisite_does_not_hide_teardown_failure(tmp_path: Path) -> None:
    result = classify_receipt(
        receipt(
            tmp_path,
            [
                report(
                    "setup",
                    "failed",
                    user_properties=[
                        ("qualification_prerequisite", "postgresql"),
                        ("qualification_reason", "missing socket"),
                    ],
                ),
                report("teardown", "failed"),
            ],
            selected=("a",),
            returncode=1,
        )
    )
    assert result["nodes"]["a"]["status"] == "failed"


def test_xfail_metadata_is_retained_and_unresolved(tmp_path: Path) -> None:
    result = classify_receipt(receipt(tmp_path, [report("call", "skipped", wasxfail="known bug")]))
    assert result["nodes"]["a"]["status"] == "blocked"
    assert result["nodes"]["a"]["reports"][0]["wasxfail"] == "known bug"


def test_truncated_stream_exit_disagreement_and_worker_loss(tmp_path: Path) -> None:
    receipt(tmp_path, [report("call")], selected=("a",))
    with (tmp_path / "reportlog.jsonl").open("a") as handle:
        handle.write('{"bad":')
    with (tmp_path / "events-controller-12.jsonl").open("a") as handle:
        handle.write(
            json.dumps({"event": "worker_down", "lost_worker": "gw2", "error": "lost"}) + "\n"
        )
    (tmp_path / "pytest.process.json").write_text('{"returncode": 2}')
    result = classify_receipt(tmp_path)
    assert result["status"] == "incomplete"
    assert result["worker_loss"][0]["lost_worker"] == "gw2"
    assert any("disagrees" in error for error in result["stream_errors"])
    assert any("truncated" in error for error in result["stream_errors"])


def test_required_union_uses_explicit_manifest(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    receipt(run, [report("setup"), report("call"), report("teardown")], selected=("a",))
    required = tmp_path / "required.json"
    required.write_text('{"selected": ["a", "other"]}')
    result = classify([run], [required])
    assert result["status"] == "not_run"
    assert result["required_unresolved"] == ["other"]


def test_old_pass_does_not_satisfy_new_native_required_manifest(tmp_path: Path) -> None:
    run = tmp_path / "old-run"
    run.mkdir()
    receipt(run, [report("setup"), report("call"), report("teardown")], selected=("a",))
    required = tmp_path / "required.json"
    required.write_text(json.dumps({"selected": ["a"], "native_required": ["a"]}))

    result = classify([run], [required])

    assert result["receipts"][0]["nodes"]["a"]["status"] == "passed"
    assert result["receipts"][0]["native_provenance"]["status"] == "unavailable"
    assert result["coverage"] == {"a": ["incomplete"]}
    assert result["required_unresolved"] == ["a"]
    assert result["status"] == "not_run"


def test_native_union_qualifies_each_node_from_its_own_context(tmp_path: Path) -> None:
    context = {
        "schema": "native-context/v1",
        "requested": {"database": "cs_sem_test"},
        "acquired": {
            "database": "cs_sem_test",
            "database_oid": 12345,
            "current_user": "corpus_sem_reader",
            "session_user": "corpus_sem_reader",
            "server_version": "18.0",
            "server_started": "2026-11-02T00:00:00+00:00",
            "host": "localhost",
            "port": 5434,
        },
        "provenance": {"complete": True, "missing": []},
    }
    output = child(
        tmp_path,
        "import pytest\n"
        "from qualification_plugin import record_native_context\n"
        "@pytest.mark.db\n"
        "def test_with_context():\n"
        f"    record_native_context({context!r})\n"
        "@pytest.mark.db\n"
        "def test_without_context():\n    pass\n",
    )
    native_nodes = [node for node in classify_receipt(output)["selected"] if "test_" in node]
    required = tmp_path / "required.json"
    required.write_text(json.dumps({"selected": native_nodes, "native_required": native_nodes}))

    result = classify([output], [required])
    qualified_node = next(node for node in native_nodes if node.endswith("test_with_context"))
    unresolved_node = next(node for node in native_nodes if node.endswith("test_without_context"))

    assert result["coverage"][qualified_node] == ["passed"]
    assert result["coverage"][unresolved_node] == ["incomplete"]
    assert result["required_unresolved"] == [unresolved_node]
    assert result["status"] == "incomplete"


def child(
    tmp_path: Path,
    source: str,
    *,
    timeout: float = 10,
    test_timeout: float = 3,
    args: tuple[str, ...] = (),
) -> Path:
    tests = tmp_path / "case"
    tests.mkdir()
    (tests / "test_case.py").write_text(source)
    config = tests / "pytest.ini"
    config.write_text("[pytest]\nmarkers = db: requires a native database context\n")
    output = tmp_path / "receipt"
    output.mkdir()
    run_python(
        output,
        ["-c", str(config), str(tests), *args],
        cwd=tests,
        timeout=timeout,
        test_timeout=test_timeout,
    )
    retained = os.environ.get("QUALIFICATION_CONTROL_RECEIPTS")
    if retained:
        target = Path(retained) / uuid.uuid4().hex
        shutil.copytree(output, target)
    return output


@pytest.mark.parametrize(
    "source,phase",
    [
        ("def test_case():\n    assert False\n", "call"),
        (
            "import pytest\n@pytest.fixture\ndef fixture():\n    yield\n    assert False\n"
            "def test_case(fixture):\n    pass\n",
            "teardown",
        ),
    ],
)
def test_real_failures(tmp_path: Path, source: str, phase: str) -> None:
    output = child(tmp_path, source)
    result = classify_receipt(output)
    assert result["status"] == "failed", (output / "pytest.stderr").read_text()
    node = next(iter(result["nodes"].values()))
    assert node["status"] == "failed"
    assert any(r["when"] == phase and r["outcome"] == "failed" for r in node["reports"])


def test_real_collection_failure(tmp_path: Path) -> None:
    output = child(tmp_path, "raise RuntimeError('collection failure')\n")
    result = classify_receipt(output)
    assert result["status"] == "failed"
    assert result["collection_errors"]


@pytest.mark.parametrize("phase", ["setup", "call", "teardown"])
def test_real_hang_retains_active_phase(tmp_path: Path, phase: str) -> None:
    source = "import pytest, time\n"
    if phase == "call":
        source += "def test_hang():\n    time.sleep(30)\n"
    else:
        source += "@pytest.fixture\ndef fixture():\n"
        source += (
            "    time.sleep(30)\n    yield\n"
            if phase == "setup"
            else ("    yield\n    time.sleep(30)\n")
        )
        source += "def test_hang(fixture):\n    pass\n"
    source += "def test_z_unstarted():\n    pass\n"
    output = child(tmp_path, source, test_timeout=0.2)
    result = classify_receipt(output)
    assert result["status"] == "incomplete", (output / "pytest.stderr").read_text()
    assert result["active_phases"][0]["phase"] == phase
    hanging = next(value for key, value in result["nodes"].items() if key.endswith("test_hang"))
    assert hanging["status"] == "incomplete"
    assert any(value["status"] == "not_run" for value in result["nodes"].values())
    if phase == "teardown":
        assert any(r["when"] == "call" and r["outcome"] == "passed" for r in hanging["reports"])


def test_parent_timeout_covers_collection(tmp_path: Path) -> None:
    output = child(tmp_path, "import time\ntime.sleep(30)\n", timeout=1, test_timeout=20)
    result = classify_receipt(output)
    assert result["status"] == "incomplete"
    assert result["process"]["interruption"] == "TimeoutExpired"
    assert not result["nodes"]  # No collection-order attribution.


def test_completed_report_survives_forced_exit(tmp_path: Path) -> None:
    output = child(
        tmp_path, "import os\ndef test_a_pass():\n    pass\ndef test_b_exit():\n    os._exit(17)\n"
    )
    result = classify_receipt(output)
    assert result["status"] == "incomplete"
    assert result["process"]["returncode"] == 17
    assert (
        next(v for k, v in result["nodes"].items() if k.endswith("test_a_pass"))["status"]
        == "passed"
    )
    assert (
        next(v for k, v in result["nodes"].items() if k.endswith("test_b_exit"))["status"]
        == "incomplete"
    )


def test_external_kill_and_launch_failure(tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.skip("owned process-group signal control requires POSIX")
    process = run_process(
        [sys.executable, "-c", "import os,signal; os.kill(os.getpid(),signal.SIGKILL)"],
        tmp_path,
        "kill",
        timeout=3,
    )
    assert process["returncode"] == -9
    failure = run_process(["/nonexistent/qualification-test"], tmp_path, "missing", timeout=3)
    assert failure["launch_error"]


def test_real_prerequisite_annotation_and_native_context(tmp_path: Path) -> None:
    output = child(
        tmp_path,
        "import pytest\n"
        "from test_prerequisites import PrerequisiteUnavailable\n"
        "from qualification_plugin import record_native_context\n"
        "@pytest.fixture\ndef fixture():\n"
        "    record_native_context({'server': 'fixture-server'})\n"
        "    raise PrerequisiteUnavailable('postgresql', 'missing native socket')\n"
        "def test_case(fixture):\n    pass\n",
    )
    result = classify_receipt(output)
    assert result["status"] == "blocked"
    assert result["process"]["returncode"] == 1  # Raw pytest setup error remains an error.
    node = next(iter(result["nodes"].values()))
    assert node["reason"] == "missing native socket"
    assert node["reports"][0]["outcome"] == "failed"
    assert result["native_contexts"][0]["context"] == {"server": "fixture-server"}
    assert result["native_contexts"][0]["nodeid"].endswith("test_case")
    assert result["native_contexts"][0]["scope"] == "test"


def test_a_required_native_test_without_acquired_context_is_incomplete(tmp_path: Path) -> None:
    output = child(
        tmp_path,
        "import pytest\n@pytest.mark.db\ndef test_case():\n    pass\n",
    )
    result = classify_receipt(output)
    nodeid = next(iter(result["selected"]))
    assert result["nodes"][nodeid]["status"] == "passed"  # raw pytest outcome is retained
    assert result["native_provenance"] == {
        "status": "incomplete",
        "required": [nodeid],
        "claimed": [nodeid],
        "unresolved": [nodeid],
        "not_claimed": [],
        "reason": "required native test has no complete item-bound acquisition context",
    }
    assert result["status"] == "incomplete"
    assert classify([output])["status"] == "incomplete"


def test_complete_native_context_is_bound_to_the_selected_node(tmp_path: Path) -> None:
    context = {
        "schema": "native-context/v1",
        "requested": {
            "server": "requested-host:5434",
            "database": "cs_sem_test",
            "principal": "corpus_sem_reader",
        },
        "acquired": {
            "server": "observed-host:5434",
            "host": "observed-host",
            "port": 5434,
            "database": "cs_sem_test",
            "database_oid": 12345,
            "current_user": "postgres",
            "session_user": "postgres",
            "server_version": "18.0",
            "server_started": "2026-11-02T00:00:00+00:00",
        },
        "provenance": {"complete": True, "missing": []},
    }
    source = (
        "import pytest\n"
        "from qualification_plugin import record_native_context\n"
        "@pytest.mark.db\n"
        "def test_case():\n"
        f"    record_native_context({context!r})\n"
    )
    output = child(tmp_path, source)
    result = classify_receipt(output)
    nodeid = next(iter(result["selected"]))
    event = result["native_contexts"][0]
    assert event["nodeid"] == nodeid and event["scope"] == "test"
    assert event["context"]["requested"]["server"] == "requested-host:5434"
    assert event["context"]["acquired"]["server"] == "observed-host:5434"
    assert result["native_provenance"]["status"] == "complete"
    assert result["native_provenance"]["unresolved"] == []
    assert result["nodes"][nodeid]["status"] == "passed"
    assert result["status"] == "passed"


@pytest.mark.parametrize(
    "field",
    [
        "host",
        "port",
        "server_started",
        "server_version",
        "database",
        "database_oid",
        "session_user",
        "current_user",
    ],
)
def test_native_context_requires_complete_acquired_identity_fields(field: str) -> None:
    context = {
        "schema": "native-context/v1",
        "requested": {},
        "acquired": {
            "host": "localhost",
            "port": 5434,
            "server_started": "2026-11-02T00:00:00+00:00",
            "server_version": "18.0",
            "database": "cs_sem_test",
            "database_oid": 12345,
            "session_user": "corpus_sem_reader",
            "current_user": "corpus_sem_reader",
        },
        "provenance": {"complete": True, "missing": []},
    }
    context["acquired"].pop(field)

    event = {"scope": "test", "nodeid": "test_case", "context": context}
    assert not _complete_native_context(event)


def test_native_context_accepts_numeric_string_port() -> None:
    context = {
        "schema": "native-context/v1",
        "requested": {},
        "acquired": {
            "host": "localhost",
            "port": "5434",
            "server_started": "2026-11-02T00:00:00+00:00",
            "server_version": "18.0",
            "database": "cs_sem_test",
            "database_oid": 12345,
            "session_user": "corpus_sem_reader",
            "current_user": "corpus_sem_reader",
        },
        "provenance": {"complete": True, "missing": []},
    }

    event = {"scope": "test", "nodeid": "test_case", "context": context}
    assert _complete_native_context(event)


def test_incomplete_or_session_only_context_does_not_attest_a_native_test(
    tmp_path: Path,
) -> None:
    incomplete = {
        "schema": "native-context/v1",
        "requested": {"database": "cs_sem_test"},
        "acquired": {
            "database": "cs_sem_test",
            "database_oid": 12345,
            "current_user": "corpus_sem_reader",
            "session_user": "corpus_sem_reader",
            "server_version": "18.0",
            "server_started": "2026-11-02T00:00:00+00:00",
            "host": "localhost",
            "port": 5434,
        },
        "provenance": {"complete": False, "missing": ["database_policy"]},
    }
    source = (
        "import pytest\n"
        "from qualification_plugin import record_native_context\n"
        "@pytest.mark.db\n"
        "def test_case():\n"
        f"    record_native_context({incomplete!r}, scope='session')\n"
    )
    output = child(tmp_path, source)
    result = classify_receipt(output)
    nodeid = next(iter(result["selected"]))
    assert result["native_contexts"][0]["nodeid"] is None
    assert result["native_provenance"]["unresolved"] == [nodeid]
    assert result["nodes"][nodeid]["status"] == "passed"
    assert result["status"] == "incomplete"


def test_pure_python_success_does_not_require_native_context(tmp_path: Path) -> None:
    output = child(tmp_path, "def test_case():\n    assert True\n")
    result = classify_receipt(output)
    assert result["status"] == "passed"
    assert result["native_provenance"]["status"] == "not_required"
    assert result["native_provenance"]["unresolved"] == []


def test_blocked_native_test_does_not_claim_a_successful_native_exercise(tmp_path: Path) -> None:
    output = child(
        tmp_path,
        "import pytest\n"
        "@pytest.mark.db\n"
        "def test_case():\n    pytest.skip('native prerequisite unavailable')\n",
    )
    result = classify_receipt(output)
    nodeid = next(iter(result["selected"]))
    assert result["nodes"][nodeid]["status"] == "blocked"
    assert result["native_provenance"]["status"] == "no_claim"
    assert result["native_provenance"]["claimed"] == []
    assert result["native_provenance"]["not_claimed"] == [nodeid]
    assert result["status"] == "blocked"


def test_legacy_receipt_keeps_its_status_without_claiming_context_completeness(
    tmp_path: Path,
) -> None:
    output = receipt(
        tmp_path, [report("setup"), report("call"), report("teardown")], selected=("a",)
    )
    result = classify_receipt(output)
    assert result["status"] == "passed"
    assert result["native_provenance"]["status"] == "unavailable"
    assert result["native_provenance"]["required"] is None


def test_real_skip_and_deselection(tmp_path: Path) -> None:
    output = child(
        tmp_path,
        "import pytest\n"
        "def test_required(request):\n"
        "    request.node.user_properties += [('qualification_prerequisite', 'corpus'),"
        " ('qualification_reason', 'no corpus')]\n"
        "    pytest.skip('no corpus')\n"
        "def test_optional(request):\n"
        "    request.node.user_properties += [('qualification_optional', 'scope exclusion')]\n"
        "    pytest.skip('scope exclusion')\n"
        "def test_excluded():\n    assert False\n",
        args=("-k", "not excluded"),
    )
    result = classify_receipt(output)
    assert result["status"] == "blocked"
    assert len(result["selected"]) == 2
    assert len(result["deselected"]) == 1
    assert not result["native_contexts"]
    assert result["session_contexts"][0]["hypothesis_profile"] == "ci"
    states = {k.rsplit("::", 1)[-1]: v["status"] for k, v in result["nodes"].items()}
    assert states == {"test_required": "blocked", "test_optional": "inapplicable"}


def test_rust_zero_tests_and_missing_junit_are_not_coverage(tmp_path: Path) -> None:
    (tmp_path / "nextest.process.json").write_text('{"returncode": 0}')
    (tmp_path / "nextest-list.stdout").write_text('{"test-count": 0}')
    assert classify_rust(tmp_path)["status"] == "not_run"
    (tmp_path / "nextest-list.stdout").write_text('{"test-count": 1}')
    assert classify_rust(tmp_path)["status"] == "incomplete"
    (tmp_path / "nextest.junit.xml").write_text(
        '<testsuites><testsuite><testcase name="native"/></testsuite></testsuites>'
    )
    assert classify_rust(tmp_path)["status"] == "passed"


@pytest.mark.parametrize(
    ("process", "count", "cases", "expected", "coverage"),
    [
        ({"returncode": 0}, 1, "<testcase name='one'/>", "passed", True),
        ({"returncode": 1}, 1, "<testcase name='one'/>", "failed", False),
        ({"returncode": 1, "cleanup_error": "drain failed"}, 1, "", "failed", False),
        ({"returncode": 0, "interruption": "SIGTERM"}, 1, "", "incomplete", False),
        ({"returncode": 0}, 2, "<testcase name='one'/>", "incomplete", False),
        ({"returncode": 0}, 1, "<testcase name='one'><skipped/></testcase>", "blocked", False),
        ({"returncode": 0}, 1, "<testcase name='one'><failure/></testcase>", "failed", False),
        ({"returncode": 0}, 0, "", "not_run", False),
    ],
)
def test_rust_artifact_outcomes_are_conservative(
    tmp_path, process, count, cases, expected, coverage
):
    (tmp_path / "nextest.process.json").write_text(json.dumps(process))
    (tmp_path / "nextest-list.stdout").write_text(json.dumps({"test-count": count}))
    (tmp_path / "nextest.junit.xml").write_text(
        f"<testsuites><testsuite>{cases}</testsuite></testsuites>"
    )
    result = classify_rust(tmp_path)
    assert result["status"] == expected
    assert result["functional_coverage"] is coverage


@pytest.mark.parametrize(
    "defect",
    [
        {"cleanup_error": "drain failed"},
        {"owned_group_cleanup": {"descendants_after_leader_exit": True}},
        {"owned_group_cleanup": {"group_present_after_cleanup": True}},
    ],
)
@pytest.mark.parametrize("count", [0, 1])
def test_rust_cleanup_defects_remain_incomplete_in_assembled_results(tmp_path, defect, count):
    receipt(tmp_path, [report("setup"), report("call"), report("teardown")], selected=("a",))
    (tmp_path / "nextest.process.json").write_text(json.dumps({"returncode": 0, **defect}))
    (tmp_path / "nextest-list.stdout").write_text(json.dumps({"test-count": count}))
    (tmp_path / "nextest.junit.xml").write_text(
        "<testsuites><testsuite><testcase name='one'/></testsuite></testsuites>"
    )
    local = classify_rust(tmp_path)
    assert local["status"] == "incomplete"
    assert not local["functional_coverage"]
    assert classify([tmp_path])["status"] == "incomplete"


def test_native_observation_requires_a_live_sink_before_any_optional_work(monkeypatch):
    import hashlib
    from types import SimpleNamespace

    from sqlalchemy.engine import make_url

    import native_test_support
    import qualification_plugin
    from corpus_structure.settings import Settings

    def forbidden(*args, **kwargs):
        pytest.fail("inactive observation must not acquire, hash, or roll back")

    # Neither import availability nor an environment setting is an active consumer.
    monkeypatch.setenv("QUALIFICATION_RECEIPT_DIR", "/unused-receipt-directory")
    monkeypatch.setattr(qualification_plugin, "_stream", None)
    monkeypatch.setattr(hashlib, "sha256", forbidden)
    previous = dict(native_test_support._DEPLOYMENTS)
    connection = SimpleNamespace(cursor=forbidden, rollback=forbidden)
    server = native_test_support.PgAdmin("postgresql://admin@db/postgres", "template", {})
    monkeypatch.setattr(server, "connect", forbidden)
    settings = Settings()
    assert not qualification_plugin.native_context_active()
    native_test_support.observe_connection(connection, make_url("postgresql://db"), purpose="read")
    native_test_support.record_server_context(settings, server)
    assert previous == native_test_support._DEPLOYMENTS

    sink = io.StringIO()
    monkeypatch.setattr(qualification_plugin, "_stream", sink)
    assert qualification_plugin.native_context_active()
    sink.close()
    assert not qualification_plugin.native_context_active()
    native_test_support.observe_connection(connection, make_url("postgresql://db"), purpose="read")
    native_test_support.record_server_context(settings, server)
    assert previous == native_test_support._DEPLOYMENTS


def test_active_native_observation_keeps_actual_identity_and_item_binding(monkeypatch):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from sqlalchemy import create_engine

    import native_test_support
    import qualification_plugin

    class Cursor:
        def __init__(self, connection):
            self.connection = connection

        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

        def execute(self, sql):
            self.connection.queries.append(sql)

        def fetchone(self):
            if "current_database()" in self.connection.queries[-1]:
                return (
                    self.connection.database,
                    self.connection.oid,
                    "actual_reader",
                    "actual_login",
                    "18.1",
                    "5434",
                    datetime(2026, 11, 5, tzinfo=UTC),
                )
            return (None,)  # A bare acquisition has no semantic revision.

    class Connection:
        autocommit = False
        info = SimpleNamespace(host="/actual/socket")

        def __init__(self, database, oid):
            self.database, self.oid = database, oid
            self.queries = []
            self.rollbacks = 0

        def cursor(self):
            return Cursor(self)

        def rollback(self):
            self.rollbacks += 1

    monkeypatch.delenv("QUALIFICATION_RECEIPT_DIR", raising=False)
    with io.StringIO() as sink:
        monkeypatch.setattr(qualification_plugin, "_stream", sink)
        monkeypatch.setattr(qualification_plugin, "_current_nodeid", "first-item")
        engine = create_engine("postgresql+psycopg://requested_user@requested_host/requested_db")
        first, second = Connection("first_clone", 1001), Connection("second_clone", 1002)
        native_test_support.observe_connection(first, engine.url, purpose="read")
        native_test_support.observe_connection(
            second, engine.url, purpose="read", nodeid="second-item"
        )
        events = [json.loads(line) for line in sink.getvalue().splitlines()]
        assert [event["nodeid"] for event in events] == ["first-item", "second-item"]
        assert [event["context"]["acquired"]["database_oid"] for event in events] == [1001, 1002]
        assert all(event["context"]["requested"]["database"] == "requested_db" for event in events)
        assert all(
            event["context"]["acquired"]["current_user"] == "actual_reader" for event in events
        )
        assert all(_complete_native_context(event) for event in events)
        for event in events:
            acquired = event["context"]["acquired"]
            assert acquired["deployment_status"] == "unavailable"
            assert acquired["revision"] is None and acquired["policy_ref"] is None
        assert first.rollbacks == second.rollbacks == 1
        sink.close()
        native_test_support.observe_connection(first, engine.url, purpose="read")
        assert len(first.queries) == 2 and first.rollbacks == 1
        engine.dispose()


def test_run_refuses_existing_invocation(tmp_path: Path) -> None:
    from test_receipts import main

    sentinel = tmp_path / "original"
    sentinel.write_text("preserved")
    with pytest.raises(FileExistsError):
        main(["run", "--out-dir", str(tmp_path), "--python-only", "--", "invalid"])
    assert list(tmp_path.iterdir()) == [sentinel]


def test_empty_rust_selection_does_not_fail_python_coverage(tmp_path: Path) -> None:
    receipt(tmp_path, [report("setup"), report("call"), report("teardown")], selected=("a",))
    (tmp_path / "nextest.process.json").write_text('{"returncode": 0}')
    (tmp_path / "nextest-list.stdout").write_text('{"test-count": 0}')
    result = classify([tmp_path])
    assert result["status"] == "passed"
    assert result["rust"][0]["status"] == "not_run"
    assert result["rust"][0]["applicability"] == "empty-selection"
    assert not result["rust"][0]["functional_coverage"]


def test_union_surfaces_source_context_differences(tmp_path: Path) -> None:
    directories = [tmp_path / "one", tmp_path / "two"]
    for index, directory in enumerate(directories):
        directory.mkdir()
        receipt(directory, [report("setup"), report("call"), report("teardown")], selected=("a",))
        (directory / "invocation.json").write_text(json.dumps({"source": {"head": str(index)}}))
    result = classify(directories)
    assert result["status"] == "passed"  # Owner judges applicability; identity is not a gate.
    assert result["source_contexts_differ"]
    assert result["contexts"][0]["invocation"]["source"]["head"] == "0"


@pytest.mark.parametrize("cancel", [False, True])
def test_cli_watchdog_overrides_and_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cancel: bool
) -> None:
    import test_receipts

    observed: dict[str, object] = {}

    def python_child(
        directory: Path, args: list[str], *, timeout: float, test_timeout: float, managed: bool
    ) -> dict[str, object]:
        assert not managed
        observed["python"] = (args, timeout, test_timeout)
        receipt(directory, [report("setup"), report("call"), report("teardown")], selected=("a",))
        return {"interruption": "KeyboardInterrupt"} if cancel else {"returncode": 0}

    def rust_child(directory: Path, *, timeout: float) -> None:
        observed["rust"] = timeout
        (directory / "rust-state.json").write_text(
            json.dumps(
                {
                    "status": "not_run",
                    "applicability": "empty-selection",
                    "functional_coverage": False,
                }
            )
        )

    monkeypatch.setattr(test_receipts, "run_python", python_child)
    monkeypatch.setattr(test_receipts, "run_rust", rust_child)
    monkeypatch.setattr(test_receipts, "source_identity", lambda: {"head": "fixture"})
    output = tmp_path / "new"
    code = test_receipts.main(
        [
            "run",
            "--out-dir",
            str(output),
            "--test-timeout",
            "7",
            "--command-timeout",
            "11",
            "--",
            "case.py",
        ]
    )
    assert observed["python"] == (["case.py"], 11, 7)
    context = json.loads((output / "invocation.json").read_text())
    assert context["test_timeout"] == 7
    assert context["session_timeout"] == 11
    if cancel:
        assert "rust" not in observed
        assert code == 1
        assert json.loads((output / "rust-state.json").read_text())["status"] == "not_run"
    else:
        assert observed["rust"] == 11
        assert code == 0


def test_rust_commands_share_bound_and_cancel_before_more_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import test_receipts

    observed: list[tuple[str, float]] = []

    def process(
        argv: list[str], directory: Path, prefix: str, **kwargs: object
    ) -> dict[str, object]:
        assert directory == tmp_path
        assert argv
        observed.append((prefix, float(str(kwargs["timeout"]))))
        return (
            {"interruption": "KeyboardInterrupt"} if prefix == "nextest-list" else {"returncode": 0}
        )

    monkeypatch.setattr(test_receipts, "run_process", process)
    test_receipts.run_rust(tmp_path, timeout=17)
    assert observed == [("rustc", 17), ("nextest-version", 17), ("nextest-list", 17)]
    assert test_receipts.classify_rust(tmp_path)["status"] == "incomplete"


@pytest.mark.parametrize("missing", ["setup", "call", "teardown"])
def test_removed_whole_phase_report_stays_incomplete(tmp_path: Path, missing: str) -> None:
    reports = [report(phase) for phase in ("setup", "call", "teardown") if phase != missing]
    result = classify_receipt(receipt(tmp_path, reports, selected=("a",)))
    assert result["status"] == "incomplete"
    assert result["nodes"]["a"]["status"] == "incomplete"
    assert result["nodes"]["a"]["reports"] == reports
    assert result["reporting_complete"]  # Valid JSONL and finish do not imply phase completeness.


@pytest.mark.parametrize("prefix", [None, "rustc", "nextest-list"])
def test_requested_rust_without_final_artifact_is_incomplete(
    tmp_path: Path, prefix: str | None
) -> None:
    receipt(tmp_path, [report("setup"), report("call"), report("teardown")], selected=("a",))
    (tmp_path / "invocation.json").write_text('{"python_only": false}')
    if prefix is not None:
        (tmp_path / f"{prefix}.process.json").write_text('{"returncode": -9}')
    result = classify([tmp_path])
    assert result["receipts"][0]["status"] == "passed"
    assert result["status"] == "incomplete"
    assert result["rust"][0]["status"] == "incomplete"
    assert not result["rust"][0]["functional_coverage"]


@pytest.mark.parametrize("exit_code", [0, 17])
def test_non_timeout_leader_exit_settles_owned_descendant(tmp_path: Path, exit_code: int) -> None:
    import subprocess
    import time

    descendant = tmp_path / "descendant.pid"
    leader_source = (
        "import os,subprocess,sys\n"
        "from pathlib import Path\n"
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])\n"
        f"Path({str(descendant)!r}).write_text(str(child.pid))\n"
        f"os._exit({exit_code})\n"
    )
    unrelated = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
    )
    try:
        result = run_process([sys.executable, "-c", leader_source], tmp_path, "leader", timeout=10)
        assert result["returncode"] == exit_code
        assert "interruption" not in result
        cleanup = result["owned_group_cleanup"]
        assert cleanup["descendants_after_leader_exit"]
        assert cleanup["signals"][0] == "SIGTERM"
        descendant_pid = int(descendant.read_text())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            proc = Path(f"/proc/{descendant_pid}/stat")
            if not proc.exists() or proc.read_text().split(")", 1)[1].split()[0] == "Z":
                break
            time.sleep(0.02)
        else:
            pytest.fail("owned descendant is still running after bounded cleanup")
        assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=5)
    retained = os.environ.get("QUALIFICATION_CONTROL_RECEIPTS")
    if retained:
        shutil.copytree(tmp_path, Path(retained) / uuid.uuid4().hex)


@pytest.mark.parametrize("termination", [signal.SIGTERM, signal.SIGINT])
def test_external_supervisor_signal_drains_group_finalizes_and_stops_rust(
    tmp_path: Path, termination: signal.Signals
) -> None:
    if os.name != "posix":
        pytest.skip("owned process-group signal control requires POSIX")
    descendant = tmp_path / "descendant.pid"
    source = tmp_path / "test_supervised.py"
    child_source = (
        "import os,signal,time; from pathlib import Path; "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        f"Path({str(descendant)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    source.write_text(
        "import subprocess,sys,time\nfrom pathlib import Path\n"
        "def test_a_completed():\n    assert 17 + 25 == 42\n"
        "def test_b_active():\n"
        f"    subprocess.Popen([sys.executable,'-c',{child_source!r}])\n"
        "    time.sleep(60)\n"
    )
    out = tmp_path / "receipts"
    script = Path(__file__).resolve().parents[2] / "scripts/test_receipts.py"
    unrelated = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True
    )
    supervisor = None
    try:
        with (
            (tmp_path / "runner.stdout").open("wb") as stdout,
            (tmp_path / "runner.stderr").open("wb") as stderr,
        ):
            supervisor = subprocess.Popen(
                [
                    sys.executable,
                    str(script),
                    "run",
                    "--out-dir",
                    str(out),
                    "--command-timeout",
                    "60",
                    "--test-timeout",
                    "60",
                    "--",
                    # Exercise the supervisor's child and its descendant without
                    # a second xdist controller buffering the inner test report.
                    "-n",
                    "0",
                    str(source),
                ],
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            deadline = time.monotonic() + 20
            while not descendant.exists() and time.monotonic() < deadline:
                assert supervisor.poll() is None, (tmp_path / "runner.stderr").read_text()
                time.sleep(0.02)
            assert descendant.exists(), "isolated active child did not start"
            started = time.monotonic()
            supervisor.send_signal(termination)
            time.sleep(0.2)
            supervisor.send_signal(termination)  # Cleanup must survive another parent signal.
            assert supervisor.wait(timeout=15) == 1
            assert time.monotonic() - started < 15
        result = json.loads((out / "classification.json").read_text())
        process = json.loads((out / "pytest.process.json").read_text())
        runner = json.loads((out / "runner.process.json").read_text())
        assert runner["interruption"] == termination.name
        assert runner["signals"] == [termination.name, termination.name]
        assert process["interruption"] == termination.name
        assert process["cancelled"] is True
        assert process["owned_group_cleanup"]["signals"] == ["SIGTERM", "SIGKILL"]
        assert result["status"] == "incomplete"
        completed = next(
            value
            for node, value in result["receipts"][0]["nodes"].items()
            if node.endswith("test_a_completed")
        )
        assert completed["status"] == "passed"
        assert json.loads((out / "rust-state.json").read_text())["status"] == "not_run"
        assert not list(out.glob("rustc.*"))
        assert not list(out.glob("nextest*"))
        pid = int(descendant.read_text())
        stat = Path(f"/proc/{pid}/stat")
        assert not stat.exists() or stat.read_text().split(")", 1)[1].split()[0] == "Z"
        assert unrelated.poll() is None
    finally:
        if supervisor is not None and supervisor.poll() is None:
            os.killpg(supervisor.pid, signal.SIGKILL)
            supervisor.wait(timeout=5)
        if descendant.exists():
            with suppress(ProcessLookupError):
                os.kill(int(descendant.read_text()), signal.SIGKILL)
        unrelated.terminate()
        unrelated.wait(timeout=5)
    retained = os.environ.get("QUALIFICATION_CONTROL_RECEIPTS")
    if retained:
        shutil.copytree(tmp_path, Path(retained) / uuid.uuid4().hex)


def test_parent_cancellation_between_commands_cannot_be_classified_as_pass(tmp_path: Path) -> None:
    receipt(tmp_path, [report("setup"), report("call"), report("teardown")], selected=("a",))
    (tmp_path / "runner.process.json").write_text('{"interruption":"SIGTERM"}')
    result = classify_receipt(tmp_path)
    assert result["status"] == "incomplete"
    assert result["nodes"]["a"]["status"] == "passed"
    assert "supervising runner interrupted" in result["stream_errors"]


def test_cleanup_error_finalizes_receipt_and_cancels_later_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import test_receipts

    def failed_cleanup(_child: object) -> dict[str, object]:
        raise RuntimeError("isolated drain failure")

    monkeypatch.setattr(test_receipts, "_stop_group", failed_cleanup)
    sentinel = tmp_path / "unexpected-later-work"
    with test_receipts.supervision(tmp_path):
        first = run_process([sys.executable, "-c", "pass"], tmp_path, "first", timeout=3)
        later = run_process(
            [sys.executable, "-c", f"from pathlib import Path; Path({str(sentinel)!r}).touch()"],
            tmp_path,
            "later",
            timeout=3,
        )
    assert first["cleanup_error"] == "RuntimeError: isolated drain failure"
    assert first["returncode"] == 0
    assert first["cancelled"] is True
    assert json.loads((tmp_path / "first.process.json").read_text()) == first
    assert later["returncode"] is None and later["cancelled"] is True
    assert not sentinel.exists()


def test_required_coverage_is_additive_and_preserves_failed_history(tmp_path, capsys):
    from test_receipts import main

    failed, repaired = tmp_path / "failed", tmp_path / "repair"
    failed.mkdir()
    repaired.mkdir()
    receipt(
        failed,
        [report("setup"), report("call", "failed"), report("teardown")],
        selected=("a",),
        returncode=1,
    )
    receipt(repaired, [report("setup"), report("call"), report("teardown")], selected=("a",))
    required = tmp_path / "required.json"
    required.write_text(json.dumps({"selected": ["a"]}))
    result = classify([failed, repaired], [required])
    assert result["status"] == "failed"
    assert result["required_node_coverage"]["status"] == "covered"
    assert result["required_node_coverage"]["unresolved"] == []
    assert (
        main(
            [
                "classify",
                "--receipt-dir",
                str(failed),
                "--receipt-dir",
                str(repaired),
                "--required-from",
                str(required),
            ]
        )
        == 1
    )
    assert json.loads(capsys.readouterr().out)["required_node_coverage"]["status"] == "covered"
    assert classify([repaired])["required_node_coverage"]["status"] == "not_declared"
    required.write_text(json.dumps({"selected": []}))
    assert classify([repaired], [required])["required_node_coverage"]["status"] == "unresolved"


@pytest.mark.parametrize("mapping", [{"a": "same", "b": "same"}, {"b": "a"}])
def test_colliding_raw_identities_cannot_absorb_a_pass(tmp_path, mapping):
    receipt(tmp_path, [report("setup"), report("call"), report("teardown")])
    path = tmp_path / "events-controller-12.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events[0]["nodeid_aliases"] = mapping
    stream(path, events)
    required = tmp_path / "required.json"
    required.write_text(json.dumps({"selected": ["a", "b"]}))
    result = classify([tmp_path], [required])
    assert result["status"] == "incomplete"
    assert result["required_node_coverage"]["status"] == "unresolved"
    assert result["required_unresolved"] == ["a", "b"]
    assert any("identity" in error for error in result["receipts"][0]["stream_errors"])


def test_serial_parallel_required_manifests_share_literal_canonical_identity(tmp_path):
    from test_receipts import _node_aliases

    serial = {"selected": ["test.py::test_a[param@a_b]"]}
    parallel = {
        "selected": ["test.py::test_a[param@a_b]@a_b"],
        "nodeid_aliases": {"test.py::test_a[param@a_b]@a_b": "test.py::test_a[param@a_b]"},
    }
    assert set(_node_aliases([serial, parallel]).values()) == {"test.py::test_a[param@a_b]"}
    run = tmp_path / "run"
    run.mkdir()
    receipt(run, [], selected=())
    paths = []
    for index, manifest in enumerate((serial, parallel)):
        path = tmp_path / f"required-{index}.json"
        path.write_text(json.dumps(manifest))
        paths.append(path)
    assert classify([run], paths)["required"] == serial["selected"]


@pytest.mark.parametrize(
    "state",
    [
        "missing",
        "empty",
        "covered",
        "prefix",
        "option",
        "argfile",
        "stale",
        "wrong_lane",
        "overwrite",
    ],
)
def test_unresolved_export_refuses_unsafe_selection(tmp_path, monkeypatch, state):
    from test_receipts import write_unresolved

    target = tmp_path / "rerun.txt"
    required = tmp_path / "required.json"
    nodes = ["test.py::test_a"]
    result = {"required": nodes, "required_unresolved": nodes, "receipts": [{}]}
    paths = [required]
    if state == "missing":
        paths = []
    if state == "empty":
        result["required"] = []
    if state == "covered":
        result["required_unresolved"] = []
    if state == "prefix":
        result["required"] = ["test.py"]
    if state == "option":
        result["required"] = ["--pyargs::test"]
    if state == "argfile":
        result["required"] = ["@selection::test"]
    if state == "overwrite":
        target.write_text("preserve\n")
    if state in {"stale", "wrong_lane"}:

        def collect(directory, args, **kwargs):
            assert "--collect-only" in args
            assert args[args.index("-n") + 1] == "0"
            assert args[args.index("-m") + 1] == "not shared_cluster_fault"
            receipt(directory, [], selected=(), returncode=4 if state == "stale" else 0)

        monkeypatch.setattr("test_receipts.run_python", collect)
    with pytest.raises(ValueError):
        write_unresolved(result, target, required_from=paths, lane="ordinary")
    if state == "overwrite":
        assert target.read_text() == "preserve\n"
    else:
        assert not target.exists()


def test_unresolved_export_fresh_collection_never_runs_body(tmp_path, monkeypatch):
    from test_receipts import write_unresolved

    case = tmp_path / "case"
    case.mkdir()
    (case / "pytest.ini").write_text("[pytest]\nmarkers = shared_cluster_fault: exclusive\n")
    (case / "test_case.py").write_text(
        "def test_case():\n    raise AssertionError('must never run')\n"
    )
    monkeypatch.chdir(case)
    target = tmp_path / "unresolved.txt"
    node = "test_case.py::test_case"
    result = {"required": [node], "required_unresolved": [node], "receipts": [{}]}
    written = write_unresolved(
        result, target, required_from=[tmp_path / "required.json"], lane="ordinary"
    )
    assert written["nodes"] == [node]
    assert target.read_text() == node + "\n"


def test_unresolved_export_preserves_configured_import_mode(tmp_path, monkeypatch):
    from test_receipts import write_unresolved

    case = tmp_path / "case"
    case.mkdir()
    (case / "pytest.ini").write_text(
        "[pytest]\n"
        "addopts = --import-mode=importlib --strict-config --strict-markers -n 2 "
        "-m shared_cluster_fault\n"
        "markers = shared_cluster_fault: exclusive\n"
    )
    nodes = []
    # Importlib gives equal file basenames separate identities without __init__.py files.
    for namespace in ("left", "right"):
        directory = case / namespace
        directory.mkdir()
        (directory / "test_same.py").write_text(
            "def test_case():\n    raise AssertionError('collection must never run bodies')\n"
        )
        nodes.append(f"{namespace}/test_same.py::test_case")
    required = case / "required.json"
    required.write_text(json.dumps({"selected": nodes}))
    monkeypatch.chdir(case)
    target = tmp_path / "unresolved.txt"
    result = {"required": nodes, "required_unresolved": nodes, "receipts": [{}]}
    written = write_unresolved(result, target, required_from=[required], lane="ordinary")

    assert target.read_text().splitlines() == nodes
    collected = classify_receipt(Path(written["validation_receipt"]))
    assert collected["selected"] == sorted(nodes)
    assert collected["worker_facts"]["created"] == []
    assert collected["session_contexts"][0]["requested_worker_selection"] == 0


@pytest.mark.parametrize("manifest", [None, {"event": "collection_finish", "selected": ["other"]}])
def test_uncollected_report_pass_cannot_cover_current_required_node(tmp_path, manifest):
    receipt(tmp_path, [report("setup"), report("call"), report("teardown")], selected=("a",))
    path = tmp_path / "events-controller-12.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    events = events[1:]
    if manifest is not None:
        events.insert(0, manifest)
    stream(path, events)
    required = tmp_path / "required.json"
    required.write_text(json.dumps({"selected": ["a"]}))
    result = classify([tmp_path], [required])
    assert result["receipts"][0]["nodes"]["a"]["status"] == "passed"
    assert result["required_node_coverage"]["status"] == "unresolved"
    assert result["required_unresolved"] == ["a"]


@pytest.mark.parametrize(
    "args",
    [
        ["-p", "no:qualification_plugin"],
        ["-o", "addopts="],
        ["--report-log", "caller.jsonl"],
        ["-m", "shared_cluster_fault"],
        ["-n", "0"],
        ["@caller.txt"],
        ["-k", "--quiet"],
        ["tests/../../main.py"],
    ],
)
def test_managed_pytest_forwarding_rejects_policy_overrides(args: list[str]) -> None:
    from test_receipts import validate_pytest_args

    with pytest.raises(ValueError):
        validate_pytest_args(args)


def test_managed_fault_retry_keeps_only_owned_selection(tmp_path: Path) -> None:
    from test_receipts import _managed_pytest_args

    selection = tmp_path / "retry.txt"
    node = "tests/scripts/test_native_auth.py::test_crash_recovery[spaces and $literal]"
    selection.write_text(node + "\n")
    args = _managed_pytest_args(
        [], lane="fault", directory=tmp_path / "fault", selection_file=selection
    )
    assert args == ["-n", "0", "-m", "shared_cluster_fault", node]
    assert _managed_pytest_args(
        ["-k", "recovery and not held"],
        lane="fault",
        directory=tmp_path / "fault",
        selection_file=None,
    ) == [
        "-n",
        "0",
        "-m",
        "shared_cluster_fault",
        "tests/scripts/test_native_auth.py",
        "-k",
        "recovery and not held",
    ]
    selection.write_text("-p\nno:qualification_plugin\n")
    with pytest.raises(ValueError, match="canonical"):
        _managed_pytest_args(
            [], lane="fault", directory=tmp_path / "fault", selection_file=selection
        )


def test_receipt_distinguishes_empty_selection_from_test_failure(tmp_path: Path) -> None:
    directory = receipt(tmp_path, [], selected=(), returncode=5)
    stream(
        directory / "events-controller-12.jsonl",
        [{"event": "collection_finish", "selected": [], "pid": 12, "worker": "controller"}],
    )
    outcome = classify([directory])
    assert outcome["status"] == "not_run"
    assert outcome["receipts"][0]["empty_selection"]
    assert outcome["receipts"][0]["process"]["returncode"] == 5


def test_nextest_holds_actual_target_report_lock_through_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import fcntl

    import test_receipts

    report_directory = tmp_path / "shared-target" / "nextest" / "qualification"
    junit = report_directory / "junit.xml"
    copyfile = shutil.copyfile

    def assert_locked() -> None:
        with (
            (report_directory / ".junit.lock").open("a") as competing,
            pytest.raises(BlockingIOError),
        ):
            fcntl.flock(competing, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def process(
        argv: list[str], directory: Path, prefix: str, **kwargs: object
    ) -> dict[str, object]:
        assert argv
        if prefix == "nextest-list":
            (directory / "nextest-list.stdout").write_text(
                json.dumps(
                    {"rust-build-meta": {"target-directory": str(tmp_path / "shared-target")}}
                )
            )
        if prefix == "nextest":
            assert_locked()
            junit.write_text("<testsuites/>")
        return {"returncode": 0}

    def capture(source: Path, destination: Path) -> Path:
        assert_locked()
        return copyfile(source, destination)

    monkeypatch.setattr(test_receipts, "run_process", process)
    monkeypatch.setattr(shutil, "copyfile", capture)
    test_receipts.run_rust(tmp_path, timeout=2)
    assert (tmp_path / "nextest.junit.xml").read_text() == "<testsuites/>"
