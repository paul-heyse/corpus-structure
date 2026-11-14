"""Actual semantic CLI source selection, automated routing and protected lifecycle controls."""

import json
from contextlib import contextmanager

from typer.testing import CliRunner


def test_cli_finalization_returns_real_receipt_and_exact_replay(
    domain_default_case, tmp_path, monkeypatch
):
    commit_writer_engine = domain_default_case.writer
    from corpus_structure.cli import orchestrate as cli
    from corpus_structure.cli.app import app

    _, run, _ = domain_default_case.stage.result

    @contextmanager
    def engine(_, **kwargs):
        yield commit_writer_engine

    monkeypatch.setattr(cli, "ENGINE", engine)
    runner = CliRunner()
    result = runner.invoke(
        app, ["run", "finalize", str(run), "--output-realization", "evaluated", "--json"]
    )
    assert result.exit_code == 0, (result.output, result.exception)
    first = json.loads(result.stdout)
    assert (
        first["run_id"] == run
        and first["realization_id"] == "evaluated"
        and first["receipt"]["data_revision"] == 1
    )
    replay = runner.invoke(
        app, ["run", "finalize", str(run), "--output-realization", "evaluated", "--json"]
    )
    assert replay.exit_code == 0, (replay.output, replay.exception)
    assert json.loads(replay.stdout) == first
