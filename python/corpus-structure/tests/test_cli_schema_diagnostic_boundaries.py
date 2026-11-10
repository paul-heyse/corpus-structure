"""Actual schema adapters preserve operation meaning at optional custody boundaries."""

import json
from contextlib import nullcontext

import pytest

from corpus_structure.cli.managed import ResultStore
from corpus_structure.semantic.refusals import SemanticRefusal


@pytest.fixture(scope="module")
def toy_preparation():
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.regeneration import acquire_packs, prepare_release

    bundle, dependencies, profile = acquire_packs((DOMAINS / "toy",))
    return bundle, dependencies, profile, prepare_release(bundle, dependencies, profile)


def prepared_route(monkeypatch, toy_preparation):
    from corpus_structure.semantic import regeneration

    bundle, dependencies, profile, prepared = toy_preparation
    monkeypatch.setattr(
        regeneration, "acquire_packs", lambda *args: (bundle, dependencies, profile)
    )
    monkeypatch.setattr(regeneration, "prepare_release", lambda *args: prepared)
    return prepared


@pytest.mark.parametrize("command", ("compile", "check", "released-check"))
def test_success_survives_optional_publication_failure(
    cli, tmp_path, monkeypatch, toy_preparation, command
):
    from corpus_structure.cli import diagnostic_artifacts
    from corpus_structure.semantic import query, releases, runtime

    prepared = prepared_route(monkeypatch, toy_preparation)
    if command == "released-check":
        monkeypatch.setattr(runtime, "open_runtime_engine", lambda *a, **k: nullcontext(object()))
        monkeypatch.setattr(query, "read_snapshot", lambda engine: nullcontext(object()))
        monkeypatch.setattr(releases, "verify_release", lambda conn, release: prepared)
        arguments = ["schema", "check", "--release", prepared.release_id]
    else:
        arguments = ["schema", command, "--domain", "toy"]
    control = cli(*arguments, "--json")
    assert control.exit_code == 0, control.output
    expected = json.loads(control.stdout)
    primary = OSError("password=private-publication-value")

    def fail(*args, **kwargs):
        raise primary

    monkeypatch.setattr(diagnostic_artifacts, "publish_diagnostic", fail)
    root = tmp_path / "results"
    target = tmp_path / "output"
    if command == "compile":
        arguments += ["--out", str(target)]
    result = cli(
        *arguments, "--retain-diagnostics", "--json", env={"CORPUS_CI_RESULTS": str(root)}
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    for key in ("release_id", "execution_model_id", "artifacts"):
        assert report[key] == expected[key]
    for key in ("validation_outcome", "complete", "observations"):
        assert report["validation"][key] == expected["validation"][key]
    evidence = report["validation"]["evidence"]
    assert evidence["kind"] == "marker" and "OSError" in evidence["reason"]
    assert evidence["engine"] == expected["validation"]["evidence"]["engine"]
    assert evidence["sensitivity"] == expected["validation"]["evidence"]["sensitivity"]
    assert "private-publication-value" not in result.output
    (manifest,) = ResultStore(root).list(None, 20, None).results
    assert manifest.outcome == "passed" and manifest.settled is not None
    assert manifest.details["diagnostic_unavailable"] == evidence["reason"]
    assert "diagnostic-report" not in manifest.artifacts
    if command == "compile":
        assert (target / "manifest.json").read_bytes() == prepared.manifest
        assert list(target.glob("*.artifact"))


@pytest.mark.parametrize("expected", (False, True))
def test_retained_schema_failure_classification_and_replay(
    cli, tmp_path, monkeypatch, toy_preparation, expected
):
    from corpus_structure.semantic import regeneration

    prepared_route(monkeypatch, toy_preparation)
    child = RuntimeError("password=private-exception-value")
    child.add_note("child note")
    group = ExceptionGroup("schema group", [child])
    group.add_note("group note")
    primary = SemanticRefusal("controlled refusal") if expected else group
    calls = []

    def fail(*args, **kwargs):
        calls.append("prepare")
        try:
            raise ValueError("cause note")
        except ValueError as cause:
            raise primary from cause

    monkeypatch.setattr(regeneration, "prepare_release", fail)
    env = {"CORPUS_CI_RESULTS": str(tmp_path)}
    failed = cli("schema", "check", "--domain", "toy", "--retain-diagnostics", "--json", env=env)
    assert failed.exit_code == 1
    assert calls == ["prepare"]
    if not expected:
        assert failed.exception is primary
    (manifest,) = ResultStore(tmp_path).list(None, 20, None).results
    assert manifest.outcome == "failed" and manifest.settled is not None

    def forbidden(*args, **kwargs):
        pytest.fail("retained inspection executed preparation")

    monkeypatch.setattr(regeneration, "prepare_release", forbidden)
    inspected = cli("results", "inspect", manifest.id, "--view", "observations", "--json", env=env)
    assert inspected.exit_code == 0, inspected.output
    value = json.loads(inspected.stdout)
    traces = [row["exception"] for row in value["observations"]["rows"] if row["exception"]]
    diagnostic = cli("schema", "diagnostic", manifest.id, "--json", env=env)
    if expected:
        assert not traces
        assert diagnostic.exit_code == 0, diagnostic.output
        assert "diagnostic-report" in manifest.artifacts
    else:
        assert diagnostic.exit_code == 1
        assert "diagnostic-report" not in manifest.artifacts
        (trace,) = traces
        root, cause = trace["stacks"]
        assert root["exc_type"] == "ExceptionGroup" and root["is_group"]
        assert root["exc_notes"] == ["group note"]
        assert cause["exc_type"] == "ValueError" and cause["is_cause"]
        (branch,) = root["exceptions"]
        assert branch["stacks"][0]["exc_type"] == "RuntimeError"
        assert branch["stacks"][0]["exc_notes"] == ["child note"]
        assert root["frames"] and all("locals" not in frame for frame in root["frames"])
        assert "private-exception-value" not in inspected.output


def test_required_output_write_failure_keeps_original_error(
    cli, tmp_path, monkeypatch, toy_preparation
):
    from pathlib import Path

    prepared_route(monkeypatch, toy_preparation)
    primary = OSError("controlled required output failure")
    target = tmp_path / "output"
    write = Path.write_bytes

    def fail(path, content):
        if path == target / "manifest.json":
            raise primary
        return write(path, content)

    monkeypatch.setattr(Path, "write_bytes", fail)
    root = tmp_path / "results"
    result = cli(
        "schema", "compile", "--domain", "toy", "--out", str(target),
        "--retain-diagnostics", "--json", env={"CORPUS_CI_RESULTS": str(root)}
    )
    assert result.exit_code != 0 and result.exception is primary
    assert not result.stdout
    (manifest,) = ResultStore(root).list(None, 20, None).results
    assert manifest.outcome == "failed"


def test_optional_publication_never_swallows_cancellation(tmp_path, monkeypatch, toy_preparation):
    from corpus_structure.cli import diagnostic_artifacts
    from corpus_structure.semantic.operation_reporting import projection_validation_report
    from corpus_structure.semantic.refusals import FailureContext

    _, _, _, prepared = toy_preparation
    report = projection_validation_report(prepared)
    primary = KeyboardInterrupt("cancel publication")

    def fail(*args, **kwargs):
        raise primary

    monkeypatch.setattr(diagnostic_artifacts, "publish_diagnostic", fail)
    with (
        pytest.raises(KeyboardInterrupt) as caught,
        ResultStore(tmp_path).operation("schema.check", observations=True) as invocation,
    ):
        diagnostic_artifacts.retain_optional_diagnostic(
            invocation, report, context=FailureContext().bind(prepared)
        )
    assert caught.value is primary
    (manifest,) = ResultStore(tmp_path).list(None, 20, None).results
    assert manifest.outcome == "interrupted"


@pytest.mark.parametrize("raw", (False, True))
def test_unavailable_marker_preserves_disclosure_assessment_and_minimum_budget(raw):
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operation_reporting import (
        unavailable_validation_evidence,
        validation_failure_report,
    )

    original = validation_failure_report(
        SemanticRefusal("controlled refusal"), raw_evidence=raw, max_bytes=1024
    )
    selected = unavailable_validation_evidence(original, "Diagnostic publication unavailable.")
    before, after = original.model_dump(mode="json"), selected.model_dump(mode="json")
    assert after["validation_outcome"] == before["validation_outcome"]
    assert after["complete"] == before["complete"]
    assert after["evidence"]["kind"] == "marker"
    assert after["evidence"]["engine"] == before["evidence"]["engine"]
    assert after["evidence"]["sensitivity"] == ("raw" if raw else "safe")
    assert len(canonical_bytes(after)) <= 1024


def test_failed_optional_report_construction_keeps_original_preparation_diagnostics(
    cli, tmp_path, monkeypatch
):
    from corpus_structure.semantic import regeneration
    from corpus_structure.semantic.refusals import FailureContext
    from corpus_structure.semantic.types import Diagnostic, PreparationError

    primary = PreparationError((Diagnostic("original_invalid", "original.path", "original"),))
    secondary = PreparationError((Diagnostic("secondary_invalid", "report.path", "secondary"),))

    def fail_inputs(*args, **kwargs):
        raise primary

    def fail_report(*args, **kwargs):
        raise secondary

    monkeypatch.setattr(regeneration, "acquire_packs", fail_inputs)
    monkeypatch.setattr(FailureContext, "report", fail_report)
    result = cli(
        "schema", "check", "--retain-diagnostics", "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert result.exit_code == 1
    (item,) = json.loads(result.stdout)["error"]["diagnostics"]
    assert item["code"] == "original_invalid" and item["location"] == "original.path"
    assert "secondary_invalid" not in result.stdout
    (manifest,) = ResultStore(tmp_path).list(None, 20, None).results
    assert manifest.outcome == "failed" and "diagnostic-report" not in manifest.artifacts


@pytest.mark.parametrize("preparation", (False, True))
@pytest.mark.parametrize("secondary_preparation", (False, True))
@pytest.mark.parametrize("json_mode", (False, True))
def test_secondary_reporting_failure_preserves_refusal_once(
    cli, tmp_path, monkeypatch, preparation, secondary_preparation, json_mode
):
    from corpus_structure.semantic import regeneration
    from corpus_structure.semantic.refusals import FailureContext
    from corpus_structure.semantic.types import Diagnostic, PreparationError

    primary = (
        PreparationError((Diagnostic("original_invalid", "original.path", "original"),))
        if preparation else SemanticRefusal("original refusal")
    )
    secondary = (
        PreparationError((Diagnostic("secondary_invalid", "report.path", "secondary"),))
        if secondary_preparation else RuntimeError("password=private-report-failure")
    )
    reports = []

    def fail_inputs(*args, **kwargs):
        raise primary

    def fail_report(self, error):
        assert error is primary
        reports.append(error)
        raise secondary

    monkeypatch.setattr(regeneration, "acquire_packs", fail_inputs)
    monkeypatch.setattr(FailureContext, "report", fail_report)
    args = ["schema", "check", "--retain-diagnostics"]
    if json_mode:
        args += ["--json"]
    result = cli(*args, env={"CORPUS_CI_RESULTS": str(tmp_path)})
    assert result.exit_code == 1 and reports == [primary]
    assert "private-report-failure" not in result.output
    (manifest,) = ResultStore(tmp_path).list(None, 20, None).results
    account = manifest.operation_account
    assert account is not None and account.failure is not None
    assert account.failure.kind == "refusal" and account.failure.code == type(primary).__name__
    assert manifest.outcome == "failed"
    inspected = cli(
        "results", "inspect", manifest.id, "--view", "observations", "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert inspected.exit_code == 0, inspected.output
    assert not any(row["exception"] for row in json.loads(inspected.stdout)["observations"]["rows"])
    if json_mode:
        detail = json.loads(result.stdout)["error"]
        assert detail["code"] == type(primary).__name__
        assert "unavailable" in detail["diagnostic_unavailable"]
        assert "validation" not in detail
        if preparation:
            assert detail["diagnostics"][0]["code"] == "original_invalid"
    else:
        assert "unavailable" in result.stderr and "refused:" in result.stderr


@pytest.mark.parametrize("json_mode", (False, True))
def test_unretained_reporting_failure_preserves_original_refusal(
    cli, tmp_path, monkeypatch, json_mode
):
    from corpus_structure.semantic import regeneration
    from corpus_structure.semantic.refusals import FailureContext

    primary = SemanticRefusal("original refusal")
    reports = []

    def fail_inputs(*args, **kwargs):
        raise primary

    def fail_report(self, error):
        reports.append(error)
        raise RuntimeError("password=private-report-failure")

    monkeypatch.setattr(regeneration, "acquire_packs", fail_inputs)
    monkeypatch.setattr(FailureContext, "report", fail_report)
    arguments = ["schema", "check", *(["--json"] if json_mode else [])]
    result = cli(*arguments, env={"CORPUS_CI_RESULTS": str(tmp_path)})
    assert result.exit_code == 1 and reports == [primary]
    assert "private-report-failure" not in result.output
    assert not ResultStore(tmp_path).list(None, 20, None).results
    if json_mode:
        detail = json.loads(result.stdout)["error"]
        assert detail["code"] == "SemanticRefusal" and detail["message"] == "original refusal"
        assert "unavailable" in detail["diagnostic_unavailable"] and "validation" not in detail
    else:
        assert "unavailable" in result.stderr and "refused: original refusal" in result.stderr


@pytest.mark.parametrize("nested", (False, True))
def test_actual_retained_unraised_cause_has_explicit_original_link_omission(
    cli, tmp_path, monkeypatch, toy_preparation, nested
):
    from corpus_structure.semantic import regeneration

    prepared_route(monkeypatch, toy_preparation)
    primary = None

    def fail(*args, **kwargs):
        nonlocal primary
        try:
            raise RuntimeError("original child") from ValueError("unraised cause")
        except RuntimeError as child:
            if nested:
                primary = ExceptionGroup("outer group", [child])
                # Child membership supplies the relationship; suppress the duplicate context.
                raise primary from None
            primary = child
            raise

    monkeypatch.setattr(regeneration, "prepare_release", fail)
    env = {"CORPUS_CI_RESULTS": str(tmp_path)}
    result = cli("schema", "check", "--domain", "toy", "--retain-diagnostics", "--json", env=env)
    assert result.exit_code == 1 and result.exception is primary
    (manifest,) = ResultStore(tmp_path).list(None, 20, None).results
    assert manifest.outcome == "failed" and "diagnostic-report" not in manifest.artifacts
    inspected = cli("results", "inspect", manifest.id, "--view", "observations", "--json", env=env)
    assert inspected.exit_code == 0, inspected.output
    traces = [row["exception"] for row in json.loads(inspected.stdout)["observations"]["rows"]
              if row["exception"]]
    (trace,) = traces
    path = "$.original.exceptions[0].__cause__" if nested else "$.original.__cause__"
    assert any(item["path"] == path and "no traceback" in item["reason"]
               for item in trace["omissions"])
