"""Installed dispatch preserves the explicit registry and loads one command family."""

import json
import subprocess
import sys
from pathlib import Path

from typer.core import TyperGroup
from typer.main import get_command

from corpus_structure.cli import REGISTRY
from corpus_structure.cli.app import build_command_app, build_full_app


def test_registry_covers_exact_installed_root_names():
    command = get_command(build_full_app())
    assert isinstance(command, TyperGroup)
    assert set(command.commands) == {name for entry in REGISTRY for name in entry.names}


def test_installed_entrypoint_reimport_leaves_spawned_worker_before_model_setup():
    # multiprocessing re-executes the console script as __mp_main__ before the
    # child can install custody checks for generated dependency code.
    entrypoint = Path(sys.executable).with_name("ci")
    script = """
import runpy
import sys
runpy.run_path(sys.argv[1], run_name="__mp_main__")
assert "corpus_structure.cli.output" not in sys.modules
assert "typing_inspection.typing_objects" not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(entrypoint)], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def test_fresh_status_dispatch_imports_only_its_command_module():
    script = """
import json
import sys
from typer.testing import CliRunner
from corpus_structure.cli.app import build_command_app
app = build_command_app(["status"])
result = CliRunner().invoke(app, ["status", "--help"])
assert result.exit_code == 0, result.output
print(json.dumps(sorted(name for name in sys.modules if name.startswith("corpus_structure.cli."))))
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    modules = json.loads(result.stdout)
    assert modules == [
        "corpus_structure.cli.app",
        "corpus_structure.cli.output",
        "corpus_structure.cli.status",
    ]


def test_full_modes_and_unknown_names_keep_complete_registration(monkeypatch):
    for arguments in ([], ["--help"], ["status", "--help"], ["unknown"], ["--show-completion"]):
        assert build_command_app(arguments) is build_full_app()
    monkeypatch.setenv("_CI_COMPLETE", "bash_complete")
    assert build_command_app(["status"]) is build_full_app()


def test_partial_then_full_registration_retains_nested_commands_without_duplicates():
    for family, nested in (("model", "source"), ("demands", "graph")):
        command = get_command(build_command_app([family]))
        assert isinstance(command, TyperGroup)
        group = command.commands[family]
        assert isinstance(group, TyperGroup)
        assert nested in group.commands
    full = get_command(build_full_app())
    assert isinstance(full, TyperGroup)
    model = full.commands["model"]
    demands = full.commands["demands"]
    assert isinstance(model, TyperGroup)
    assert isinstance(demands, TyperGroup)
    assert "source" in model.commands
    assert "graph" in demands.commands


def test_main_preserves_test_argument_boundary(monkeypatch):
    from corpus_structure.cli import app as entrypoint
    from corpus_structure.cli.output import CliState

    selections: list[list[str]] = []
    calls: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def select(arguments: list[str]):
        selections.append(arguments)

        def invoke(*, args: list[str], obj: CliState):
            calls.append((tuple(args), obj.test_args))

        return invoke

    monkeypatch.setattr(entrypoint, "build_command_app", select)
    monkeypatch.setattr(sys, "argv", ["ci", "test", "--json", "--", "--help", "test_one.py"])
    entrypoint.main()
    assert selections == [["test", "--json"]]
    assert calls == [(("test", "--json"), ("--help", "test_one.py"))]
