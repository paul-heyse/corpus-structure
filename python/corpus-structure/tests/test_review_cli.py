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
    retained = tmp_path / "managed" / original["invocation_id"] / "selection.json"
    retained.write_text(
        '{"structural_selections":[{"run_id":205,"cut_id":283,"kind":"artifact_identity"}]}'
    )
    edited = cli("review", "retry", original["invocation_id"], "--json")
    assert edited.exit_code == 1
    assert "selection differs" in json.loads(edited.stdout)["error"]["message"]
    assert len(seen) == 2


def test_review_retry_requires_settled_cleanup(cli, tmp_path, monkeypatch):
    from corpus_structure.serve import review_bundle

    selection = tmp_path / "selection.json"
    selection.write_text('{"structural_selections":[{"run_id":205,"cut_id":283}]}')
    results = tmp_path / "managed"

    def uncertain(_request, _destination, _settings, *, retain_binding, **_kwargs):
        retain_binding("bound-source")
        error = ValueError("capture owner lost its connection")
        error.add_note("database cleanup failed")
        raise error

    monkeypatch.setenv("CORPUS_CI_RESULTS", str(results))
    monkeypatch.setattr(review_bundle, "export_review_bundle", uncertain)
    failed = cli("review", "export", str(selection), "--exact-closure", "--json")
    assert failed.exit_code == 1
    manifest_path = next(results.glob("*/manifest.json"))
    manifest = json.loads(manifest_path.read_text())
    assert manifest["details"]["custody_unsettled"] is True
    retry = cli("review", "retry", manifest["id"], "--json")
    assert retry.exit_code == 1
    assert "proof that the previous capture settled" in json.loads(retry.stdout)["error"]["message"]


def test_managed_inspection_matches_detached_and_rejects_replacement(cli, tmp_path, monkeypatch):
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.serve.contributions import ContributionRequest
    from corpus_structure.serve.review_bundle import ReviewSelection, write_review_bundle

    root = tmp_path / "managed"
    monkeypatch.setenv("CORPUS_CI_RESULTS", str(root))
    with ResultStore(root).operation("review.export") as invocation:
        bundle = invocation.directory / "bundle"
        selection = ReviewSelection(
            selections=(ContributionRequest(run_id=1),), completeness="inventory"
        )
        write_review_bundle(selection, bundle, [("contributions", {"id": "known"})])
        invocation.publish("bundle", bundle)

    detached = cli("review", "inspect", str(bundle), "--json")
    managed = cli("review", "inspect", "--result", invocation.id, "--json")
    assert detached.exit_code == managed.exit_code == 0, managed.output
    assert json.loads(managed.stdout) == {"result_id": invocation.id, **json.loads(detached.stdout)}
    assert json.loads(managed.stdout)["relations"] == {"contributions": 1}
    assert cli("review", "inspect", str(bundle), "--result", invocation.id).exit_code == 2

    bundle.rename(bundle.with_name("previous"))
    bundle.mkdir()
    replaced = cli("review", "inspect", "--result", invocation.id, "--json")
    assert replaced.exit_code == 1
    assert "differs from its owner publication" in json.loads(replaced.stdout)["error"]["message"]


def test_piped_review_selection_is_bounded_before_delivery(cli, monkeypatch):
    from corpus_structure.cli import review
    from corpus_structure.cli.app import app

    admitted = []

    def deliver(_ctx, request, destination, *, exact_closure, json):
        admitted.append((request.selections[0].run_id, destination, exact_closure, json))

    monkeypatch.setattr(review, "_deliver_review", deliver)
    args = ["review", "export", "-", "--exact-closure", "--json"]
    passed = cli.runner.invoke(app, args, input=b'{"selections":[{"run_id":17}]}')
    assert passed.exit_code == 0, passed.output
    assert admitted == [(17, None, True, True)]

    oversized = cli.runner.invoke(app, args, input=b"x" * (8 * 1024 * 1024 + 1))
    assert oversized.exit_code == 1
    assert "8 MiB limit" in json.loads(oversized.stdout)["error"]["message"]
    assert admitted == [(17, None, True, True)]

    malformed = cli.runner.invoke(app, args, input=b"{")
    assert malformed.exit_code == 1
    assert admitted == [(17, None, True, True)]
