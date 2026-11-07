"""The CLI contract (foundations §3.1, D8 §4; interfaces note §3)."""

from __future__ import annotations

import json
from contextlib import contextmanager
from subprocess import CompletedProcess
from typing import Any

import pytest
from psycopg_pool import PoolTimeout

from corpus_structure.cli import orchestrate
from corpus_structure.settings import Settings, SettingsReport

GROUPS = (
    "db", "schema", "ingest", "project", "run", "status", "tasks", "query", "explain", "golden",
    "eval", "mcp", "direct", "context", "doctor", "setup", "results", "test", "promote", "model",
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

    monkeypatch.setattr(orchestrate, "READ_ENGINE", unreachable)


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


def test_removed_placeholder_is_not_executable(cli) -> None:
    result = cli("experiment", settings=refuse)
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "experiment" in result.stderr


def test_a_mistyped_field_inside_a_section_is_refused(cli) -> None:
    # A name that reaches a section meets its extra="forbid"; only names outside every section
    # are silently ignored, which is what the report's unknown list catches.
    result = cli("status", settings=lambda: Settings(), env={"CORPUS_PATHS__DATA_DIRR": "x"})
    assert result.exit_code == 1
    assert "data_dirr" in result.stderr


def test_recipe_redacts_before_clipping(cli, monkeypatch):
    from corpus_structure.cli import operations

    child = "postgresql://user:example-secret@localhost/db" + "x" * 11960
    child += "\npassword='example quoted secret' token=\x1b[31manother-secret\x1b[0m"
    monkeypatch.setattr(
        operations, "run_recipe", lambda *a, **kw: CompletedProcess([], 0, child, "")
    )
    result = cli("check", "--only", "lint", "--json")
    assert result.exit_code == 0
    output = json.loads(result.stdout)["output"]
    assert all(
        secret not in output for secret in ("example-secret", "quoted secret", "another-secret")
    )


def test_context_reports_winning_setting_source(cli, tmp_path):
    result = cli(
        "context",
        "show",
        "--json",
        settings=lambda: Settings(database={"pool_max_size": 5}),
        env={
            "CORPUS_CI_RESULTS": str(tmp_path),
            "CORPUS_DATABASE__POOL_MAX_SIZE": "6",
            "CORPUS_DATABASE__POOL_MIN_SIZE": "0",
        },
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["results"] == str(tmp_path)
    assert "CORPUS_CI_RESULTS" not in report["settings"]["unknown_env"]
    assert report["settings"]["origins"]["database.pool_max_size"] == "constructor"
    assert report["settings"]["origins"]["database.pool_min_size"] == "environment"
    assert report["observed_binding"] is None


def test_retain_evidence_survives_managed_expiry(cli, tmp_path, monkeypatch):
    from corpus_evidence.store import content_hash, load
    from corpus_structure.cli import operations
    from corpus_structure.cli.managed import ResultStore

    evidence = tmp_path / "docs/design_review/evidence"
    evidence.mkdir(parents=True)
    results = tmp_path / "results"
    store = ResultStore(results)
    with store.operation("test", scope={"consumer": "CLI-CA02"}) as invocation:
        selection = invocation.directory / "selection.json"
        selection.write_text("{}\n", encoding="utf-8")
        invocation.publish("selection", selection)
        artifact = invocation.directory / "summary.txt"
        artifact.write_text("bounded closure\n", encoding="utf-8")
        invocation.publish("bundle", artifact)
        invocation.settle("passed")
    monkeypatch.setattr(operations, "checkout", lambda ctx: tmp_path)
    indexed = []

    def index(*args):
        indexed.append(args)
        return CompletedProcess([], 0, "", "")

    monkeypatch.setattr(operations, "run_recipe", index)
    result = cli(
        "evidence", "retain", invocation.id, "--json", env={"CORPUS_CI_RESULTS": str(results)}
    )
    assert result.exit_code == 0, result.output
    assert indexed == [("evidence", "index")]
    expiry = store.show(invocation.id).expiry()
    assert store.collect(apply=True, now=expiry + 1).removed == [invocation.id]
    saved = load(evidence)
    assert not saved.load_errors
    [(folder, record)] = saved.all_records()
    assert record.consumed_by == ["CLI-CA02"]
    assert record.outcome == "passed"
    assert json.loads((folder.path / "invocation.json").read_text())["artifact_role"] == "bundle"
    for _, ref in record.files:
        assert ref.sha256 == content_hash(folder.path / ref.path)
    assert (folder.path / "raw/summary.txt").read_text(encoding="utf-8") == "bounded closure\n"


def test_coverage_keeps_failed_required_lane_without_a_receipt(cli, tmp_path, monkeypatch):
    from corpus_structure.cli import testing
    from corpus_structure.cli.managed import ResultStore

    with ResultStore(tmp_path).operation("test", scope={"lane": "all"}) as attempt:
        ordinary = attempt.directory / "ordinary"
        ordinary.mkdir()
        attempt.publish("ordinary", ordinary)
        attempt.settle("failed", lanes={"ordinary": "passed", "fault": "failed"})
    monkeypatch.setattr(
        testing,
        "_supervisor",
        lambda *a, **kw: {
            "status": "passed",
            "required_node_coverage": {"status": "covered", "unresolved": []},
            "source_contexts_differ": False,
            "contexts": [],
            "missing_lanes": ["fault"],
            "lane_selections": {"ordinary": str(ordinary)},
        },
    )
    result = cli("test", "coverage", attempt.id, "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)})
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "incomplete"
    assert report["missing_lanes"] == ["fault"]
    assert report["node_coverage"]["status"] == "unresolved"
    assert report["attempt_outcomes"] == {attempt.id: "failed"}


def test_installed_coverage_refuses_substituted_receipt_member(cli, tmp_path):
    from corpus_structure.cli.managed import ResultStore

    external = tmp_path / "unowned.jsonl"
    external.write_text("must not be read", encoding="utf-8")
    with ResultStore(tmp_path / "results").operation("test", scope={"lane": "ordinary"}) as attempt:
        ordinary = attempt.directory / "ordinary"
        ordinary.mkdir()
        (ordinary / "reportlog.jsonl").symlink_to(external)
        attempt.publish("ordinary", ordinary)
        attempt.settle("passed", lanes={"ordinary": "passed"})
    result = cli(
        "test",
        "coverage",
        attempt.id,
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path / "results")},
    )
    assert result.exit_code == 1, result.output
    assert json.loads(result.stdout)["error"]["code"] == "ResultError"
    assert "reportlog.jsonl" in result.stdout
    assert "must not be read" not in result.output


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
assert result.exit_code == (2 if sys.argv[1] == '["experiment"]' else 0), result.output
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
