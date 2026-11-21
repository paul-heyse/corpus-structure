"""Operation-boundary policy resolution and complete custody settings."""

import json

import pytest
import typer

from corpus_structure.cli.characterization_options import execution_methods
from corpus_structure.settings import Settings, settings_report


def test_environment_policy_and_file_override_share_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("CORPUS_CHARACTERIZATION_EXECUTION__MAX_REGIONS", "3")
    monkeypatch.setenv("CORPUS_NEMOTRON__ENDPOINT", "http://127.0.0.1:18035/v1")
    settings = Settings()
    assert settings.characterization_execution.max_regions == 3
    assert (
        "CORPUS_CHARACTERIZATION_EXECUTION__MAX_REGIONS"
        not in settings_report(settings).unknown_env
    )
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"workers": 1, "max_submissions": 1}))
    resolved, fields = execution_methods(settings, policy)
    assert resolved.execution_policy.max_regions == 3
    assert resolved.execution_policy.workers == 1
    assert resolved.nemotron_endpoint == "http://127.0.0.1:18035/v1"
    assert resolved.nemotron_receipts == settings.nemotron.receipts
    assert fields == ("max_submissions", "workers")


@pytest.mark.parametrize("body", [{"max_regions": 0}, {"unknown_limit": 2}, []])
def test_invalid_policy_refuses_before_execution(tmp_path, body):
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(body))
    with pytest.raises(typer.BadParameter):
        execution_methods(Settings(), policy)


def test_exact_policy_resume_uses_retained_values_before_explicit_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("CORPUS_CHARACTERIZATION_EXECUTION__MAX_REGIONS", "3")
    initial, _ = execution_methods(Settings())
    monkeypatch.setenv("CORPUS_CHARACTERIZATION_EXECUTION__MAX_REGIONS", "7")
    policy = tmp_path / "policy.json"
    policy.write_text('{"workers":1}')
    resumed, fields = execution_methods(Settings(), policy, inherited=initial.execution_policy)
    assert resumed.execution_policy.max_regions == 3
    assert resumed.execution_policy.workers == 1
    assert fields == ("workers",)


@pytest.mark.parametrize("content", ['{"workers":1,"workers":2}', "", '{"workers":"private"}'])
def test_policy_rejects_invalid_files_without_echoing_values(tmp_path, content):
    policy = tmp_path / "policy.json"
    policy.write_text(content)
    with pytest.raises(typer.BadParameter) as error:
        execution_methods(Settings(), policy)
    assert "private" not in str(error.value)
