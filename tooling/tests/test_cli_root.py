from typer.testing import CliRunner

from corpus_tooling.cli import app


def test_help_lists_the_command() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Repository tooling" in result.stdout
