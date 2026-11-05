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
    monkeypatch.setattr(review_bundle, "export_review_bundle", lambda *args, **kwargs: {"ok": True})
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
