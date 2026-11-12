"""Operation-boundary policy resolution and complete custody settings."""

import json

import pytest
import typer

from corpus_structure.cli.characterization_options import method_settings
from corpus_structure.settings import Settings, settings_report


def test_environment_policy_and_file_override_share_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("CORPUS_CHARACTERIZATION_EXECUTION__MAX_REGIONS", "3")
    settings = Settings()
    assert settings.characterization_execution.max_regions == 3
    assert (
        "CORPUS_CHARACTERIZATION_EXECUTION__MAX_REGIONS"
        not in settings_report(settings).unknown_env
    )
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"workers": 1, "max_submissions": 1}))
    resolved = method_settings(settings, policy)
    assert resolved.execution_policy.max_regions == 3
    assert resolved.execution_policy.workers == 1
    assert resolved.nemotron_endpoint == settings.nemotron.endpoint
    assert resolved.nemotron_receipts == settings.nemotron.receipts


@pytest.mark.parametrize("body", [{"max_regions": 0}, {"unknown_limit": 2}, []])
def test_invalid_policy_refuses_before_execution(tmp_path, body):
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(body))
    with pytest.raises(typer.BadParameter):
        method_settings(Settings(), policy)
