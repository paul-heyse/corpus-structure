"""Managed routing controls; synthetic receipts establish no provider functional evidence."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from corpus_structure.cli.managed import OperationAccount, ResultStore


def invoke(cli, store, *args, selectors=()):
    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState

    return cli.runner.invoke(
        app,
        ["test", *args],
        obj=CliState(test_args=selectors),
        env={"CORPUS_CI_RESULTS": str(store.root)},
    )


@pytest.mark.parametrize("empty", [False, True])
def test_providers_only_routes_one_python_lane_and_persists_selection(
    cli, tmp_path, monkeypatch, empty
):
    from corpus_structure.cli import testing

    store = ResultStore(tmp_path / "results")
    monkeypatch.setattr(testing, "_validate", lambda args: False)
    calls = []

    def recipe(name, *args, env):
        calls.append(name)
        assert name == "test-all"
        assert env["CORPUS_CI_EVIDENCE_SELECTION"] == "providers"
        assert env["CORPUS_CI_PYTHON_ONLY"] == "1"
        directory = Path(env["CORPUS_CI_RECEIPT_DIR"])
        directory.mkdir()
        (directory / "classification.json").write_text("{}")
        return subprocess.CompletedProcess(
            [],
            1,
            json.dumps(
                {
                    "counts": {"selected": 0 if empty else 1},
                    "workers": {"requested": "auto", "actual": 1},
                    "custody_unsettled": False,
                    "retryable": not empty,
                    "status": "not_run" if empty else "blocked",
                    "empty": empty,
                    "evidence_selection": "providers",
                }
            ),
            "",
        )

    monkeypatch.setattr(testing, "run_recipe", recipe)
    answer = invoke(cli, store, "--providers-only", "--json")
    assert answer.exit_code == 1, answer.output
    report = json.loads(answer.stdout)
    assert report["outcome"] == ("not_run" if empty else "blocked")
    manifest = store.show(report["id"])
    assert manifest.scope["evidence_selection"] == "providers"
    assert manifest.scope["required_lanes"] == ["ordinary"]
    assert calls == ["test-all"]
    if not empty:
        assert report["next_action"] == f"ci test retry {report['id']} --lane ordinary"


def test_providers_fault_refuses_before_validation_or_store(cli, tmp_path, monkeypatch):
    from corpus_structure.cli import testing

    def unexpected(*args, **kwargs):
        pytest.fail("incompatible selection must refuse before setup")

    monkeypatch.setattr(testing, "_validate", unexpected)
    monkeypatch.setattr(testing, "result_store", unexpected)
    answer = cli("test", "--providers-only", "--lane", "fault", "--json")
    assert answer.exit_code == 1
    assert (
        "incompatible with the exclusive fault lane"
        in json.loads(answer.stdout)["error"]["message"]
    )


def test_not_run_is_a_terminal_managed_outcome_and_operation_account(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("test", scope={"evidence_selection": "providers"}) as result:
        result.settle("not_run")
    assert store.show(result.id).outcome == "not_run"
    assert OperationAccount(outcome="not_run", cleanup="established").outcome == "not_run"


def test_collection_routes_serial_inventory_and_reports_no_execution(cli, tmp_path, monkeypatch):
    from corpus_structure.cli import testing

    store = ResultStore(tmp_path / "results")
    monkeypatch.setattr(testing, "_validate", lambda args: bool(args))

    def recipe(name, *args, env):
        assert name == "test-all"
        assert env["CORPUS_CI_COLLECTION_ONLY"] == "1"
        assert env["CORPUS_CI_PYTHON_ONLY"] == "1"
        assert env["CORPUS_CI_EVIDENCE_SELECTION"] == "ordinary"
        assert "CORPUS_CI_TEST_WORKERS" not in env
        assert args == ("python/corpus-structure/tests",)
        directory = Path(env["CORPUS_CI_RECEIPT_DIR"])
        directory.mkdir()
        (directory / "classification.json").write_text("{}")
        return subprocess.CompletedProcess(
            [],
            0,
            json.dumps(
                {
                    "collection_outcome": "passed",
                    "counts": {"selected": 2, "not_run": 2},
                    "workers": {"requested": 0, "actual": 0},
                    "custody_unsettled": False,
                    "retryable": False,
                    "status": "not_run",
                    "empty": False,
                }
            ),
            "",
        )

    monkeypatch.setattr(testing, "run_recipe", recipe)
    # Collection success and functional execution are separate reported facts.
    answer = invoke(cli, store, "collect", "--json", selectors=("python/corpus-structure/tests",))
    assert answer.exit_code == 0, answer.output
    report = json.loads(answer.stdout)
    assert report["outcome"] == "passed"
    assert report["collection_outcome"] == "passed"
    assert report["execution_outcome"] == "not_run"
    manifest = store.show(report["id"])
    assert manifest.action == "test.collect"
    assert manifest.scope["collection_only"]
    assert manifest.details["execution_outcome"] == "not_run"


def test_collection_receipts_are_rejected_for_functional_coverage_and_retry(cli, tmp_path):
    store = ResultStore(tmp_path / "results")
    with store.operation("test.collect", scope={"collection_only": True}) as result:
        result.settle("passed", execution_outcome="not_run", collection_outcome="passed")
    for command in (("coverage", result.id), ("retry", result.id)):
        answer = invoke(cli, store, *command, "--json")
        assert answer.exit_code == 1
        assert "collection-only receipts" in json.loads(answer.stdout)["error"]["message"]


def test_manual_retry_inherits_provider_mode_instead_of_ordinary_defaults(
    cli, tmp_path, monkeypatch
):
    from corpus_structure.cli import testing

    store = ResultStore(tmp_path / "results")
    node = "tests/test_provider_probe.py::test_case"
    with store.operation(
        "test", scope={"lane": "ordinary", "evidence_selection": "providers"}
    ) as original:
        directory = original.directory / "ordinary"
        directory.mkdir()
        (directory / "fixture").write_text("retained original routing receipt")
        original.publish("ordinary", directory)
        original.settle("blocked", lanes={"ordinary": "blocked"})
    calls = []

    def supervisor(*args, **kwargs):
        if args == ("context",):
            return {}
        if "--write-unresolved" in args:
            Path(args[args.index("--write-unresolved") + 1]).write_text(node + "\n")
        return {
            "custody_unsettled": False,
            "retryable": True,
            "required_unresolved": [node],
            "contexts": [{"invocation": {"evidence_selection": "providers"}}],
        }

    def recipe(name, *args, env):
        assert name == "test-all"
        assert env["CORPUS_CI_EVIDENCE_SELECTION"] == "providers"
        assert env["CORPUS_CI_TEST_WORKERS"] == "2"
        assert Path(env["CORPUS_CI_SELECTION_FILE"]).read_text() == node + "\n"
        directory = Path(env["CORPUS_CI_RECEIPT_DIR"])
        directory.mkdir()
        (directory / "classification.json").write_text("{}")
        calls.append(name)
        return subprocess.CompletedProcess(
            [],
            1,
            json.dumps(
                {
                    "counts": {"selected": 1},
                    "workers": {"requested": 2, "actual": 1},
                    "custody_unsettled": False,
                    "retryable": True,
                    "status": "blocked",
                    "empty": False,
                }
            ),
            "",
        )

    monkeypatch.setenv("CORPUS_CI_EVIDENCE_SELECTION", "ordinary")
    monkeypatch.setattr(testing, "_supervisor", supervisor)
    monkeypatch.setattr(testing, "run_recipe", recipe)
    answer = invoke(cli, store, "retry", original.id, "--workers", "2", "--json")
    assert answer.exit_code == 1, answer.output
    report = json.loads(answer.stdout)
    assert store.show(report["id"]).scope["evidence_selection"] == "providers"
    assert store.show(original.id).outcome == "blocked"
    assert calls == ["test-all"]


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("ordinary", "ci test collect"),
        ("providers", "ci test collect --providers-only"),
    ],
)
def test_collection_failure_hint_preserves_collection_intent(tmp_path, mode, expected):
    from corpus_structure.cli.testing import _next_test_action

    store = ResultStore(tmp_path)
    with store.operation("test.collect", scope={"evidence_selection": mode}) as result:
        result.settle("failed")
    assert (
        _next_test_action(
            store.show(result.id), {"ordinary": "failed"}, {"ordinary"}, receipt_unsettled=False
        )
        == expected
    )
