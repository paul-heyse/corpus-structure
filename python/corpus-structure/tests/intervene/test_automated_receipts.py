"""Subprocess isolation/capture controls, independent of an extraction provider."""

import io
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from corpus_structure.intervene import automated
from corpus_structure.semantic.operations import OperationConflict
from corpus_structure.settings import Settings


def test_capture_drains_but_retains_only_declared_bound(tmp_path, monkeypatch):
    monkeypatch.setattr(automated, "_RAW_LIMIT", 4)
    state = {}
    automated._capture_pipe(io.BytesIO(b"0123456789"), tmp_path / "output", state)
    assert (tmp_path / "output").read_bytes() == b"0123"
    assert state == {"bytes": 10, "retained_bytes": 4, "truncated": True}


def test_provider_environment_excludes_database_evaluator_and_shell_injection(monkeypatch):
    for key in (
        "PGPASSWORD",
        "DATABASE_URL",
        "CORPUS_EVALUATOR_DSN",
        "UV_LOCKED",
        "BASH_ENV",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDECODE",
        "PWD",
        "OLDPWD",
    ):
        monkeypatch.setenv(key, "must not reach the source author")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "provider-token")
    environment = automated._provider_environment()
    assert environment["ANTHROPIC_API_KEY"] == "provider-token"
    assert not any(key.startswith(("PG", "DATABASE", "CORPUS_", "UV_")) for key in environment)
    assert not set(environment) & {
        "BASH_ENV",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDECODE",
        "PWD",
        "OLDPWD",
    }


@pytest.mark.parametrize("mode", ["success", "failure", "timeout"])
def test_invocation_retains_raw_output_for_success_failure_and_timeout(tmp_path, monkeypatch, mode):
    script = tmp_path / "provider"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json,sys,time\n"
        "print(json.dumps({'session_id':'fixture-session','is_error':False}),flush=True)\n"
        "print('diagnostic-preserved',file=sys.stderr,flush=True)\n"
        + (
            "time.sleep(10)\n"
            if mode == "timeout"
            else "sys.exit(5)\n"
            if mode == "failure"
            else ""
        )
    )
    script.chmod(0o700)
    original_which = shutil.which
    monkeypatch.setattr(
        automated.shutil,
        "which",
        lambda command: str(script) if command == "claude" else original_which(command),
    )
    engine = MagicMock()
    execute = engine.connect.return_value.__enter__.return_value.execute
    execute.return_value.scalars.side_effect = [
        ["awaiting_agent"],
        ["done"],
    ]
    execute.return_value.mappings.return_value = [{"method": "agent.opus", "params": {"model": "fixture-model"}}]
    settings = Settings(paths={"data_dir": tmp_path, "model_cache": tmp_path / "cache"})
    if mode == "success":
        result = automated.extract_run(engine, settings, 17)
        assert result is not None and result.provider_session == "fixture-session"
        receipt = Path(result.receipt_dir)
    else:
        with pytest.raises(OperationConflict, match="raw receipts"):
            automated.extract_run(engine, settings, 17, timeout=0.3 if mode == "timeout" else 10)
        (receipt,) = (tmp_path / "automated-extraction" / "run-17").iterdir()
    assert json.loads((receipt / "stdout.json").read_text())["session_id"] == "fixture-session"
    assert (receipt / "stderr.log").read_text() == "diagnostic-preserved\n"
    metadata = json.loads((receipt / "invocation.json").read_text())
    assert metadata["run_id"] == 17 and not metadata["stdout"]["truncated"]
