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
        'sample: (_bundle "sample" "ok rules-scan bad later")\n'
        'interrupted: (_bundle "interrupted" "wait later")\n'
        'ok:\n    @echo "plan fake-step"\n'
        "bad:\n    @bash -c 'printf \"password=example-secret\\n\" >&2; exit 17'\n"
        'later:\n    @printf "%2000s\\n" "the later recipe ran" >&2\n'
        'wait:\n    @printf "waiting for the step\\n" >&2\n    @touch started\n    @sleep 60\n',
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
        "== just rules-scan",
        "rules-scan: not_run (no rules yet)",
        "== just bad",
        "== just later",
        "sample: 1 failed: bad (re-run one with just <id>)",
    ]
    assert "the later recipe ran" in direct.stderr

    monkeypatch.setattr(
        operations, "run_recipe_steps", lambda _: recipes.run_recipe_steps("sample")
    )
    detailed = cli("check", "--view", "steps", "--json")
    assert detailed.exit_code == 1, detailed.output
    report = json.loads(detailed.stdout)
    assert report["steps"] == [
        {"name": "ok", "outcome": "passed", "exit_code": 0, "reason": None},
        {"name": "rules-scan", "outcome": "not_run", "exit_code": 0, "reason": "no rules yet"},
        {"name": "bad", "outcome": "failed", "exit_code": 17, "reason": None},
        {"name": "later", "outcome": "passed", "exit_code": 0, "reason": None},
    ]
    (excerpt,) = report["excerpts"]
    assert (excerpt["step"], excerpt["stream"], excerpt["truncated"]) == ("bad", "stderr", False)
    assert "password=**********" in excerpt["text"]
    assert "the later recipe ran" not in excerpt["text"]
    assert "example-secret" not in detailed.stdout
    human = cli("check")
    assert human.exit_code == 1, human.output
    assert "failed (exit 17)" in human.stdout
    assert "just bad" in human.stdout


def test_single_rule_check_preserves_owner_applicability(recipe_checkout, cli):
    result = cli("check", "--only", "rules", "--view", "steps", "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["steps"] == [
        {"name": "rules-scan", "outcome": "not_run", "exit_code": 0, "reason": "no rules yet"}
    ]
    legacy = cli("check", "--only", "rules", "--json")
    assert legacy.exit_code == 0, legacy.output
    assert "rules-scan: not_run (no rules yet)" in json.loads(legacy.stdout)["output"]


def test_step_outcomes_after_owned_group_interruption(recipe_checkout):
    code = """
import json
from dataclasses import asdict
from corpus_structure.cli.recipes import run_recipe_steps
process, steps, excerpts, captured = run_recipe_steps('interrupted')
print(json.dumps([process.returncode, [asdict(step) for step in steps],
                  [asdict(excerpt) for excerpt in excerpts]]))
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
    status, steps, excerpts = json.loads(output)
    assert status == 143
    assert steps == [
        {"name": "wait", "outcome": "interrupted", "exit_code": None, "reason": None},
        {"name": "later", "outcome": "not_started", "exit_code": None, "reason": None},
    ]
    (excerpt,) = excerpts
    assert excerpt["step"] == "wait" and excerpt["stream"] == "stderr"
    assert "waiting for the step" in excerpt["text"]


def test_command_reference_direct_and_managed(cli, monkeypatch, tmp_path):
    def refuse():
        pytest.fail("command reference acquired settings or a recipe")

    monkeypatch.setattr(operations, "run_recipe", refuse)
    direct = cli("docs", "commands", "schema", "inspect", "--stdout", settings=refuse)
    assert direct.exit_code == 0, direct.output
    markdown = direct.stdout
    assert markdown.startswith("# `ci schema inspect`\n")
    assert "$ ci schema inspect [OPTIONS]" in markdown
    assert "--raw-evidence / --no-raw-evidence" in markdown
    assert "--max-errors" in markdown and "1<=x<=1000" in markdown
    assert "Example: ci schema inspect" in markdown
    assert "# `ci schema compile`" not in markdown
    assert markdown.endswith("\n") and not markdown.endswith("\n\n")
    rejected = cli("docs", "commands", "--stdout", "--json", settings=refuse)
    assert rejected.exit_code == 2, rejected.output
    managed = cli(
        "docs", "commands", "schema", "inspect", "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)}
    )
    assert managed.exit_code == 0, managed.output
    delivery = json.loads(managed.stdout)
    assert Path(delivery["path"]).read_text(encoding="utf-8") == markdown
    manifest = json.loads((Path(delivery["path"]).parent / "manifest.json").read_text())
    assert manifest["scope"] == {"command": ["schema", "inspect"]}


@pytest.mark.parametrize(
    ("tokens", "prefix"),
    [
        (["missing"], "ci"),
        (["schema", "missing"], "ci schema"),
        (["schema", "inspect", "extra"], "ci schema inspect"),
    ],
)
def test_reference_unknown_path_refuses_without_acquisition(cli, tokens, prefix):
    result = cli("docs", "commands", *tokens, "--stdout", settings=lambda: pytest.fail("settings"))
    assert result.exit_code == 2, result.output
    assert prefix in result.output and "unknown command" in result.output


def test_reference_subtree_and_sequential_isolation(cli):
    group = cli("docs", "commands", "interpretations", "--stdout")
    assert group.exit_code == 0, group.output
    assert "# `ci interpretations`" in group.stdout
    assert "`ci interpretations author`" in group.stdout
    assert "`ci schema inspect`" not in group.stdout
    author = cli("docs", "commands", "interpretations", "author", "--stdout")
    assert author.exit_code == 0, author.output
    assert "{RELEASE} {KIND} {INPUT}" in author.stdout
    assert "Structural validation" in author.stdout
    assert "private knowledge" in author.stdout
    assert "`ci interpretations lookup`" not in author.stdout


def test_reference_failed_publication_is_a_failed_managed_result(cli, monkeypatch, tmp_path):
    from corpus_structure.cli.managed import Invocation, ResultError, ResultStore

    def fail(*args, **kwargs):
        raise ResultError("publication refused")

    monkeypatch.setattr(Invocation, "publish", fail)
    result = cli(
        "docs", "commands", "schema", "inspect", "--json", env={"CORPUS_CI_RESULTS": str(tmp_path)}
    )
    assert result.exit_code == 1, result.output
    assert "publication refused" in result.output
    (manifest,) = ResultStore(tmp_path).list(None, 20, None).results
    assert manifest.outcome == "failed" and manifest.settled is not None


def test_native_step_output_survives_compact_excerpt_and_replays_by_identity(
    recipe_checkout, cli, monkeypatch
):
    payload = "EARLY_NATIVE_ERROR\n" + "detail line\n" * 3000 + "LAST_NATIVE_ERROR\n"
    producer = recipe_checkout / "wide-output.py"
    producer.write_text(
        "import sys\n"
        + f"sys.stdout.write({payload!r})\n"
        + "sys.stderr.write('password=hidden-native-secret\\n')\nsys.exit(5)\n"
    )
    with Path("justfile").open("a") as recipes_file:
        recipes_file.write(f'wide:\n    @"{sys.executable}" "{producer}"\n')
    monkeypatch.setattr(
        operations,
        "run_recipe_steps",
        lambda *args: recipes.run_recipe_steps("ci-check-only", "wide"),
    )
    root = recipe_checkout / "results"
    response = cli(
        "check",
        "--only",
        "types",
        "--view",
        "steps",
        "--json",
        env={"CORPUS_CI_RESULTS": str(root)},
    )
    assert response.exit_code == 5, response.output
    report = json.loads(response.stdout)
    assert "EARLY_NATIVE_ERROR" not in "".join(row["text"] for row in report["excerpts"])
    identity = report["invocation_id"]
    monkeypatch.setattr(
        operations, "run_recipe_steps", lambda *args: pytest.fail("output replay ran steps")
    )
    selected = cli(
        "results",
        "output",
        identity,
        "--stream",
        "stdout",
        "--step",
        "wide",
        "--json",
        env={"CORPUS_CI_RESULTS": str(root)},
    )
    assert selected.exit_code == 0, selected.output
    page = json.loads(selected.stdout)
    assert page["text"] == payload and not page["collection_truncated"]
    assert page["observed_source_bytes"] == len(payload.encode())
    error = cli(
        "results",
        "output",
        identity,
        "--stream",
        "stderr",
        "--step",
        "wide",
        "--json",
        env={"CORPUS_CI_RESULTS": str(root)},
    )
    assert error.exit_code == 0 and "hidden-native-secret" not in error.stdout
    assert "password=**********" in json.loads(error.stdout)["text"]


def test_default_json_bundle_retains_attributed_step_streams(recipe_checkout, cli, monkeypatch):
    monkeypatch.setattr(
        operations, "run_recipe_steps", lambda *args: recipes.run_recipe_steps("sample")
    )
    root = recipe_checkout / "results"
    response = cli("check", "--json", env={"CORPUS_CI_RESULTS": str(root)})
    assert response.exit_code == 1, response.output
    report = json.loads(response.stdout)
    assert "output" in report and "diagnostic" in report and "steps" not in report
    assert report["retained_output"]["availability"] == "available"
    selected = cli(
        "results",
        "output",
        report["invocation_id"],
        "--step",
        "bad",
        "--stream",
        "stderr",
        "--json",
        env={"CORPUS_CI_RESULTS": str(root)},
    )
    assert selected.exit_code == 0, selected.output
    assert "password=**********" in json.loads(selected.stdout)["text"]


def test_closed_step_channel_preserves_actual_native_exit(recipe_checkout):
    import os

    read_fd, write_fd = os.pipe()
    os.close(read_fd)
    try:
        response = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys; from corpus_structure._diagnostic_capture import _capture_step; "
                    "raise SystemExit(_capture_step('bad',int(sys.argv[1])))"
                ),
                str(write_fd),
            ],
            pass_fds=(write_fd,),
            capture_output=True,
            text=True,
        )
    finally:
        os.close(write_fd)
    assert response.returncode == 17, response.stderr


@pytest.mark.parametrize("quote", ["'", '"'])
def test_compact_excerpt_uses_safe_prefix_of_multiline_credential(recipe_checkout, quote):
    payload = "kept\npassword=" + quote + "first-secret\n" + "later-secret\n" * 16000 + quote + "\n"
    producer = recipe_checkout / "quoted-output.py"
    producer.write_text("import sys\n" + f"sys.stdout.write({payload!r})\n" + "sys.exit(17)\n")
    with Path("justfile").open("a") as recipes_file:
        recipes_file.write(f'quoted:\n    @"{sys.executable}" "{producer}"\n')
    process, _, excerpts, captured = recipes.run_recipe_steps("ci-check-only", "quoted")
    assert process.returncode == 17 and captured.availability == "available"
    selected = next(item for item in excerpts if item.stream == "stdout")
    assert selected.text == "kept" and selected.truncated
    assert selected.basis == "retained_safe_output"
    assert all(
        "first-secret" not in item.text and "later-secret" not in item.text for item in excerpts
    )
    output = next(item for item in captured.records[0].outputs if item.stream == "stdout")
    assert output.text == "kept\n" and output.observed_source_bytes == len(payload.encode())


def test_compact_excerpt_does_not_expose_detached_multiline_environment_secret(
    recipe_checkout, monkeypatch
):
    secret = "sensitive-first\n" + "sensitive-middle\n" * 1000 + "sensitive-last"
    monkeypatch.setenv("CORPUS_CAPTURE_TOKEN", secret)
    payload = "kept\n" + "ordinary-detail\n" * 10000 + secret + "\n"
    producer = recipe_checkout / "environment-output.py"
    producer.write_text("import sys\n" + f"sys.stdout.write({payload!r})\n" + "sys.exit(17)\n")
    with Path("justfile").open("a") as recipes_file:
        recipes_file.write(f'environment:\n    @"{sys.executable}" "{producer}"\n')
    process, _, excerpts, captured = recipes.run_recipe_steps("ci-check-only", "environment")
    assert process.returncode == 17 and captured.availability == "available"
    selected = next(item for item in excerpts if item.stream == "stdout")
    assert selected.basis == "retained_safe_output" and selected.truncated
    assert all(
        "sensitive-first" not in item.text
        and "sensitive-middle" not in item.text
        and "sensitive-last" not in item.text
        for item in excerpts
    )
    assert all(len(item.text) <= 1200 for item in excerpts)
