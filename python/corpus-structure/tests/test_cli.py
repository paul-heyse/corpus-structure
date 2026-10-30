"""The CLI contract (foundations §3.1, D8 §4; interfaces note §3)."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any

import pytest
from psycopg_pool import PoolTimeout

from corpus_structure.cli import orchestrate
from corpus_structure.settings import Settings, SettingsReport

GROUPS = (
    "db", "schema", "ingest", "project", "run", "status", "tasks", "query", "explain", "golden",
    "eval", "digest", "promote", "experiment", "mcp", "direct", "ack", "veto",
)  # fmt: skip


def refuse() -> Settings:
    raise AssertionError("settings were built")


def test_help_lists_groups_without_building_settings(cli) -> None:
    result = cli("--help", settings=refuse)
    assert result.exit_code == 0, result.output
    commands = result.stdout.split("Commands")[1]
    for name in GROUPS:
        assert f" {name} " in commands, name
    assert cli("status", "--help", settings=refuse).exit_code == 0
    assert cli(settings=refuse).exit_code in (0, 2)  # no_args_is_help, never settings


@pytest.fixture
def no_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """`ci status` with an unreachable database: its progress is absent, its settings report."""

    @contextmanager
    def unreachable(settings: Any, timeout: float = 30.0) -> Any:
        raise PoolTimeout("couldn't get a connection")
        yield

    monkeypatch.setattr(orchestrate, "ENGINE", unreachable)


def test_status_json_is_the_result_model(cli, no_database) -> None:
    calls = []

    def factory() -> Settings:
        calls.append(1)
        return Settings(database={"url": "postgresql:///t"})

    result = cli("status", "--json", settings=factory, env={"CORPUS_DATABSE__URL": "x"})
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    out = json.loads(result.stdout)
    assert out["progress"] is None and "PoolTimeout" in out["database_error"]
    report = SettingsReport.model_validate(out["settings"])
    assert report.resolved["database.url"] == "postgresql:///t"
    assert "CORPUS_DATABSE__URL" in report.unknown_env
    assert calls == [1]


def test_status_renders_without_json(cli, no_database) -> None:
    result = cli("status", settings=lambda: Settings(), env={"CORPUS_DATA_DIRR": "x"})
    assert result.exit_code == 0, result.output
    assert "database.template" in result.stdout
    assert "CORPUS_DATA_DIRR" in result.stdout
    assert max(len(line) for line in result.stdout.splitlines()) <= 100


def test_json_is_a_command_option_not_a_root_option(cli) -> None:
    assert cli("--json", "status", settings=lambda: Settings()).exit_code == 2


def test_planned_group_names_its_owner_on_stderr(cli) -> None:
    result = cli("experiment", settings=refuse)
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "evaluation" in result.stderr


def test_a_mistyped_field_inside_a_section_is_refused(cli) -> None:
    # A name that reaches a section meets its extra="forbid"; only names outside every section
    # are silently ignored, which is what the report's unknown list catches.
    result = cli("status", settings=lambda: Settings(), env={"CORPUS_PATHS__DATA_DIRR": "x"})
    assert result.exit_code == 1
    assert "data_dirr" in str(result.exception)


@pytest.mark.parametrize(
    "arguments", [["--help"], ["schema", "--help"], ["mcp", "--help"], ["experiment"]]
)
def test_fresh_command_registration_does_not_import_unrelated_kernels(arguments) -> None:
    import subprocess
    import sys

    script = """
import json
import sys
from typer.testing import CliRunner
from corpus_structure.cli.app import app
from corpus_structure.cli.output import CliState

def forbidden_settings():
    raise AssertionError("registration constructed settings")
result = CliRunner().invoke(
    app, json.loads(sys.argv[1]), obj=CliState(settings_factory=forbidden_settings)
)
assert result.exit_code == (1 if sys.argv[1] == '["experiment"]' else 0), result.output
for name in ("sympy", "scipy", "spacy", "pyarrow", "duckdb", "corpus_structure.semantic.prepare"):
    assert name not in sys.modules, name
"""
    result = subprocess.run(
        [sys.executable, "-c", script, json.dumps(arguments)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_archive_opening_import_does_not_acquire_current_compiler() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from corpus_structure.semantic.releases import open_release; "
            "import sys; assert 'corpus_structure.semantic.prepare' not in sys.modules",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_fresh_mcp_registration_does_not_import_analysis_or_compiler() -> None:
    import subprocess
    import sys

    script = """
import sys
from corpus_structure.intervene.semantic_server import build_semantic_server
server = build_semantic_server()
assert server.name == "corpus-structure"
for name in ("sympy", "scipy", "spacy", "pyarrow", "duckdb", "corpus_structure.semantic.prepare"):
    assert name not in sys.modules, name
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
