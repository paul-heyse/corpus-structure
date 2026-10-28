"""The CLI contract (foundations §3.1, D8 §4; interfaces note §3)."""

from __future__ import annotations

import json

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


def test_status_json_is_the_result_model(cli) -> None:
    calls = []

    def factory() -> Settings:
        calls.append(1)
        return Settings(database={"url": "postgresql:///t"})

    result = cli("status", "--json", settings=factory, env={"CORPUS_DATABSE__URL": "x"})
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    report = SettingsReport.model_validate(json.loads(result.stdout))
    assert report.resolved["database.url"] == "postgresql:///t"
    assert "CORPUS_DATABSE__URL" in report.unknown_env
    assert calls == [1]


def test_status_renders_without_json(cli) -> None:
    result = cli("status", settings=lambda: Settings(), env={"CORPUS_DATA_DIRR": "x"})
    assert result.exit_code == 0, result.output
    assert "database.template" in result.stdout
    assert "CORPUS_DATA_DIRR" in result.stdout
    assert max(len(line) for line in result.stdout.splitlines()) <= 100


def test_json_is_a_command_option_not_a_root_option(cli) -> None:
    assert cli("--json", "status", settings=lambda: Settings()).exit_code == 2


def test_planned_group_names_its_owner_on_stderr(cli) -> None:
    result = cli("schema", "compile", "--domain", "statistics", settings=refuse)
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "schema and rules" in result.stderr


def test_a_mistyped_field_inside_a_section_is_refused(cli) -> None:
    # A name that reaches a section meets its extra="forbid"; only names outside every section
    # are silently ignored, which is what the report's unknown list catches.
    result = cli("status", settings=lambda: Settings(), env={"CORPUS_PATHS__DATA_DIRR": "x"})
    assert result.exit_code == 1
    assert "data_dirr" in str(result.exception)
