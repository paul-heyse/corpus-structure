"""Recipe-owned step records and direct command reference delivery."""

import json
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from corpus_structure.cli import operations, recipes


@pytest.fixture
def recipe_checkout(tmp_path, monkeypatch):
    root = recipes.checkout()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/setup-env").touch()
    (tmp_path / "justfile").write_text(
        f"import '{root / 'justfile'}'\n"
        'sample: (_bundle "sample" "ok bad later")\n'
        'interrupted: (_bundle "interrupted" "wait later")\n'
        'ok:\n    @echo "plan fake-step"\n'
        'bad:\n    @bash -c \'printf "password=example-secret\\n" >&2; exit 17\'\n'
        'later:\n    @echo "the later recipe ran"\n'
        'wait:\n    @touch started\n    @sleep 60\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_check_step_outcomes_and_foreign_excerpt(recipe_checkout, cli, monkeypatch):
    direct = recipes.run_recipe("sample")
    assert direct.returncode == 1
    assert direct.stdout.splitlines() == [
        "== just ok",
        "plan fake-step",
        "== just bad",
        "== just later",
        "the later recipe ran",
        "sample: 1 failed: bad (re-run one with just <id>)",
    ]

    monkeypatch.setattr(
        operations, "run_recipe_steps", lambda _: recipes.run_recipe_steps("sample")
    )
    detailed = cli("check", "--view", "steps", "--json")
    assert detailed.exit_code == 1, detailed.output
    report = json.loads(detailed.stdout)
    assert report["steps"] == [
        {"name": "ok", "outcome": "passed", "exit_code": 0},
        {"name": "bad", "outcome": "failed", "exit_code": 17},
        {"name": "later", "outcome": "passed", "exit_code": 0},
    ]
    excerpts = {excerpt["stream"]: excerpt["text"] for excerpt in report["excerpts"]}
    assert "plan fake-step" in excerpts["stdout"]
    assert "password=**********" in excerpts["stderr"]
    assert "example-secret" not in detailed.stdout
    human = cli("check")
    assert human.exit_code == 1, human.output
    assert "failed (exit 17)" in human.stdout
    assert "just bad" in human.stdout


def test_step_outcomes_after_owned_group_interruption(recipe_checkout):
    code = """
import json
from dataclasses import asdict
from corpus_structure.cli.recipes import run_recipe_steps
process, steps = run_recipe_steps('interrupted')
print(json.dumps([process.returncode, [asdict(step) for step in steps]]))
"""
    with subprocess.Popen(
        [sys.executable, "-c", code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as child:
        try:
            deadline = time.monotonic() + 10
            while not Path("started").is_file() and child.poll() is None:
                if time.monotonic() >= deadline:
                    pytest.fail("fixture recipe did not start")
                time.sleep(0.02)
            assert Path("started").is_file()
            child.send_signal(signal.SIGTERM)
            output, diagnostics = child.communicate(timeout=10)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()
    assert child.returncode == 0, diagnostics
    assert json.loads(output) == [
        143,
        [
            {"name": "wait", "outcome": "interrupted", "exit_code": None},
            {"name": "later", "outcome": "not_started", "exit_code": None},
        ],
    ]


def test_command_reference_direct_and_managed(cli, monkeypatch, tmp_path):
    def refuse_settings():
        pytest.fail("direct command reference acquired settings")

    calls = []
    markdown = "# ci\n\n## ci check\n"

    def reference(name):
        calls.append(name)
        return subprocess.CompletedProcess([], 0, markdown, "")

    monkeypatch.setattr(operations, "run_recipe", reference)
    direct = cli("docs", "commands", "--stdout", settings=refuse_settings)
    assert (direct.exit_code, direct.stdout, direct.stderr) == (0, markdown, "")

    rejected = cli("docs", "commands", "--stdout", "--json", settings=refuse_settings)
    assert rejected.exit_code == 2, rejected.output
    assert calls == ["ci-reference"]

    managed = cli("docs", "commands", "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)})
    assert managed.exit_code == 0, managed.output
    delivery = json.loads(managed.stdout)
    assert Path(delivery["path"]).read_text(encoding="utf-8") == markdown
    assert calls == ["ci-reference", "ci-reference"]
