"""Failed commands and malformed reports cannot masquerade as clean lint."""

import json
import shutil
import subprocess

import pytest
from schema_lint_support import report_errors


@pytest.mark.parametrize("report", ["[]", '[{"level":"warning","message":"warning"}]'])
def test_clean_and_allowed_warning_reports(report):
    assert report_errors(subprocess.CompletedProcess([], 0, report, "")) == []


@pytest.mark.parametrize(
    "code,report",
    [(2, "[]"), (2, ""), (0, ""), (0, "{}"), (0, '[{"level":"error","message":"bad"}]')],
)
def test_failed_or_malformed_report_is_not_clean(code, report):
    with pytest.raises((AssertionError, json.JSONDecodeError)):
        report_errors(
            subprocess.CompletedProcess([], code, report, "argument/configuration failure")
        )


def test_expected_rule_error_retains_message():
    result = subprocess.CompletedProcess([], 2, '[{"level":"error","message":"bad"}]', "")
    assert report_errors(result, expected_returncode=2) == ["bad"]


def test_actual_warning_only_cli_and_argument_failure(tmp_path):
    schema = tmp_path / "warning.yaml"
    schema.write_text("id: https://example.org/lint\nname: lint\nclasses:\n  bad_name: {}\n")
    config = tmp_path / "lint.yaml"
    config.write_text("rules:\n  standard_naming:\n    level: warning\n")
    executable = shutil.which("linkml-lint")
    assert executable is not None
    arguments = [executable, "--ignore-warnings", "--format", "json", "--config"]
    result = subprocess.run(
        [*arguments, str(config), str(schema)], capture_output=True, text=True, check=False
    )
    assert report_errors(result) == []
    assert any(p["level"] == "warning" for p in json.loads(result.stdout))
    failed = subprocess.run(
        [*arguments, str(tmp_path / "missing.yaml"), str(schema)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode != 0 and failed.stdout == "" and failed.stderr
    with pytest.raises(AssertionError):
        report_errors(failed)
