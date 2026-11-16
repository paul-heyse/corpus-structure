"""Current selected review transport; controlled routes grant no native authority."""

import json
from contextlib import contextmanager

import pytest


@pytest.mark.parametrize("name", ("retained-review", "retained-golden", "retained-eval"))
def test_retired_frontdoors_are_absent_before_settings(cli, name):
    def refuse():
        raise AssertionError("retired frontdoor acquired runtime settings")

    result = cli(name, "--help", settings=refuse)
    assert result.exit_code == 2
    assert "No such command" in result.output


def test_current_reference_assessment_review_help_is_lazy(cli):
    def refuse():
        raise AssertionError("command help acquired runtime settings")

    for arguments in (
        ("review", "export", "--help"),
        ("review", "verify", "--help"),
        ("golden", "author", "--help"),
        ("golden", "snapshot", "--help"),
        ("eval", "run", "--help"),
        ("eval", "records", "--help"),
        ("eval", "structural", "--help"),
        ("eval", "fit-features", "--help"),
        ("structure", "export", "--help"),
        ("structure", "verify", "--help"),
        ("mcp", "evaluator", "--help"),
    ):
        result = cli(*arguments, settings=refuse)
        assert result.exit_code == 0, result.output


@pytest.mark.parametrize("targets", [("structure.admit",), ("record_policy.grade",)])
def test_structural_admission_cli_requires_its_exact_target_and_evaluator_purpose(
    cli, monkeypatch, tmp_path, targets
):
    from corpus_structure.semantic import runtime
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_service import DemandRoot, NativeDemandRequest

    request = NativeDemandRequest(
        project_id="unadmitted-project",
        release_id="unadmitted-release",
        runtime_id="unadmitted-runtime",
        roots=(
            DemandRoot(subject="comparison", original_source="original:one", analyzed_scope={}),
        ),
        targets=targets,
        execution_profile="controlled-adapter",
    )
    path = tmp_path / "structural.json"
    path.write_bytes(json_bytes(request.model_dump(mode="python")))
    acquired = []
    sentinel = RuntimeError("stop before database acquisition")

    def acquire(*args, purpose, **kwargs):
        acquired.append(purpose)
        raise sentinel

    monkeypatch.setattr(runtime, "open_runtime_engine", acquire)
    result = cli(
        "eval", "structural", "--request", str(path), "--source-root", str(tmp_path), "--json"
    )
    if targets == ("structure.admit",):
        assert acquired == ["evaluate"]
        assert result.exception is sentinel
    else:
        assert acquired == []
        assert result.exit_code != 0
        assert "exactly its adjudication target" in result.output


def test_current_review_export_uses_exact_native_demand_and_reader_transaction(
    cli, tmp_path, monkeypatch
):
    from corpus_structure.semantic import runtime
    from corpus_structure.serve import demand_export

    state = {"active": False}
    seen = []
    connection = object()

    class Engine:
        @contextmanager
        def begin(self):
            state["active"] = True
            try:
                yield connection
            finally:
                state["active"] = False

    @contextmanager
    def engine(settings, application_name, *, purpose):
        assert purpose == "read"
        yield Engine()

    def export(actual_connection, demand, **kwargs):
        assert state["active"] and actual_connection is connection
        seen.append((demand, kwargs))
        return {"version": "controlled-native-export"}

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(demand_export, "export_demand_result", export)
    destination = tmp_path / "current-native-review"
    result = cli(
        "review",
        "export",
        "--demand",
        "demand:actual",
        "--project",
        "project:actual",
        "--out",
        str(destination),
        "--format",
        "jsonl",
        "--page-rows",
        "2",
        "--page-bytes",
        "2048",
        "--json",
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assert seen == [
        (
            "demand:actual",
            dict(
                project_id="project:actual",
                destination=destination,
                format="jsonl",
                page_rows=2,
                page_bytes=2048,
            ),
        )
    ]
    assert json.loads(result.stdout) == {
        "path": str(destination),
        "manifest": {"version": "controlled-native-export"},
    }
    assert not state["active"]


def test_current_review_verify_is_offline_and_requires_trusted_manifest_digest(
    cli, tmp_path, monkeypatch
):
    from corpus_structure.serve import demand_export

    def refuse():
        raise AssertionError("offline native verification acquired runtime settings")

    seen = []
    monkeypatch.setattr(
        demand_export,
        "verify_demand_export",
        lambda path, **kwargs: seen.append((path, kwargs)) or {"verified": True},
    )
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    missing = cli("review", "verify", str(artifact), "--json", settings=refuse)
    assert missing.exit_code == 2 and seen == []
    result = cli(
        "review", "verify", str(artifact), "--manifest-digest", "a" * 64, "--json", settings=refuse
    )
    assert result.exit_code == 0, (result.output, result.exception)
    assert seen == [(artifact, {"manifest_digest": "a" * 64})]
    assert json.loads(result.stdout) == {"verified": True}


def test_current_explain_forwards_actual_selected_product_support(cli, monkeypatch):
    from corpus_structure.cli import selected_results

    calls = []
    monkeypatch.setattr(
        selected_results, "query", lambda *args, **kwargs: calls.append((args[1:], kwargs))
    )
    result = cli(
        "explain",
        "--demand",
        "demand:A",
        "--project",
        "project:A",
        "--product",
        "product:A",
        "--json",
    )
    assert result.exit_code == 0, result.output
    assert calls[0][0] == ("support", "demand:A", "project:A")
    assert calls[0][1]["product"] == "product:A"
