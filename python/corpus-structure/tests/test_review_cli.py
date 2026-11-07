"""Offline review entrypoints do not construct database settings."""

import json
from contextlib import contextmanager


def test_review_help_is_lazy(cli):
    def refuse():
        raise AssertionError("settings should be lazy")

    for arguments in (
        ("review", "--help"),
        ("review", "verify", "--help"),
        ("structure", "list", "--help"),
    ):
        result = cli(*arguments, settings=refuse)
        assert result.exit_code == 0, result.output


def test_offline_verify_refuses_missing_bundle_without_settings(cli, tmp_path):
    def refuse():
        raise AssertionError("offline verification opened settings")

    result = cli("review", "verify", str(tmp_path / "missing"), "--json", settings=refuse)
    assert result.exit_code == 1
    error = json.loads(result.stdout)["error"]
    assert error["code"] == "ValueError"
    assert error["message"] == "review member missing or not an ordinary file"


def test_mixed_cohort_export_keeps_project_and_authorization_boundaries(cli, tmp_path, monkeypatch):
    from corpus_structure.evaluate import review_assessments
    from corpus_structure.semantic import runtime
    from corpus_structure.serve import review_bundle
    from corpus_structure.settings import Settings

    selected = tmp_path / "selection.json"
    selected.write_text('{"selections":[{"run_id":45}]}')
    exposures = []
    purposes = []

    class Engine:
        @contextmanager
        def begin(self):
            yield object()

    @contextmanager
    def engine(*args, **kwargs):
        purposes.append(kwargs["purpose"])
        yield Engine()

    def record_exposure(conn, **kwargs):
        exposures.append(kwargs)
        return len(exposures)

    monkeypatch.setattr(runtime, "open_runtime_engine", engine)
    monkeypatch.setattr(review_assessments, "record_review_exposure", record_exposure)

    def export(_request, destination, _settings, **_kwargs):
        destination.mkdir()
        return {"ok": True}

    monkeypatch.setenv("CORPUS_CI_RESULTS", str(tmp_path / "managed"))
    monkeypatch.setattr(review_bundle, "export_review_bundle", export)
    result = cli(
        "review",
        "export-evaluated",
        str(selected),
        str(tmp_path / "bundle"),
        "--project",
        "m1-source-grinstead-snell",
        "--assessment-set",
        "18",
        "--group-project",
        "pce-statistics-structural",
        "--group-assessment-set",
        "7",
        "--authorization-basis",
        "selected already-exposed development cohort",
        "--json",
        settings=lambda: Settings(),
    )
    assert result.exit_code == 0, result.output
    assert purposes == ["evaluate"]
    assert [
        (value["project_id"], value["group"], value["authorization_basis"]) for value in exposures
    ] == [
        ("m1-source-grinstead-snell", False, "selected already-exposed development cohort"),
        ("pce-statistics-structural", True, None),
    ]


def test_managed_review_export_retries_the_recorded_exact_selection(cli, tmp_path, monkeypatch):
    from corpus_structure.serve import review_bundle

    selected = tmp_path / "selection.json"
    selected.write_text('{"structural_selections":[{"run_id":205,"cut_id":283}]}')
    seen = []
    source_binding = "bound-source"

    def export(request, destination, _settings, *, exact_closure, retain_binding, **_kwargs):
        retain_binding(source_binding)
        seen.append((request, exact_closure))
        destination.mkdir()
        return {"selection": request.model_dump(mode="json")}

    monkeypatch.setenv("CORPUS_CI_RESULTS", str(tmp_path / "managed"))
    monkeypatch.setattr(review_bundle, "export_review_bundle", export)
    first = cli("review", "export", str(selected), "--exact-closure", "--json")
    assert first.exit_code == 0, first.output
    original = json.loads(first.stdout)
    selected.unlink()
    retry = cli("review", "retry", original["invocation_id"], "--json")
    assert retry.exit_code == 0, retry.output
    retried = json.loads(retry.stdout)
    assert retried["invocation_id"] != original["invocation_id"]
    assert seen[0] == seen[1] and seen[1][1] is True
    assert retried["selection"] == original["selection"]
    source_binding = "different-source"
    changed = cli("review", "retry", original["invocation_id"], "--json")
    assert changed.exit_code == 1
    assert "differ from the original" in json.loads(changed.stdout)["error"]["message"]
    assert len(seen) == 2
