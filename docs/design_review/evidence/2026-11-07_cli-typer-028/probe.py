"""Compare Typer releases against the same Python, Rich and CLI source."""

import json
import os
import platform
import subprocess
import sys
from importlib.metadata import version
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

import typer
from rich.console import Console
from rich.text import Text
from typer.testing import CliRunner

app = typer.Typer()


@app.command()
def fixture(
    ctx: typer.Context,
    item_count: Annotated[int, typer.Option(metavar="ITEM-COUNT")] = 1,
    strict: Annotated[bool | None, typer.Option("--strict/--no-strict")] = None,
    alias: Annotated[str, typer.Option("--explicit-alias", metavar="ALIAS")] = "default",
) -> None:
    typer.echo(json.dumps([item_count, strict, alias, ctx.get_parameter_source("strict").name]))


def complete(ctx: typer.Context, args: list[str], incomplete: str) -> list[str]:
    typer.echo(json.dumps([args, ctx.params, incomplete]), err=True)
    return ["alpha", "beta"]


@app.command()
def discover(
    profile: Annotated[str, typer.Option()] = "normal",
    item: Annotated[str, typer.Option(autocompletion=complete)] = "",
) -> None:
    raise AssertionError((profile, item))


def check_callbacks(runner: CliRunner) -> None:
    events = []

    def record(ctx: typer.Context, value: str) -> str:
        events.append((value, dict(ctx.params)))
        return value

    local = typer.Typer()

    @local.command()
    def invoke(
        first: Annotated[str, typer.Option(callback=record)] = "first-default",
        second: Annotated[str, typer.Option(callback=record)] = "second-default",
    ) -> None:
        typer.echo(f"{first}:{second}")

    explicit = runner.invoke(local, ["--second", "chosen"])
    assert (explicit.exit_code, explicit.stdout) == (0, "first-default:chosen\n"), explicit.output
    assert events == [("chosen", {}), ("first-default", {"second": "chosen"})], events
    events.clear()
    defaults = runner.invoke(local, [])
    assert defaults.exit_code == 0, defaults.output
    assert events == [("first-default", {}), ("second-default", {"first": "first-default"})], events


def check_fixture() -> None:
    runner = CliRunner()
    expected_flag = "--ITEM-COUNT" if typer.__version__ == "0.27.3" else "--item-count"
    for flags, expected in [
        ([], [1, None, "default", "DEFAULT"]),
        (["--strict"], [1, True, "default", "COMMANDLINE"]),
        (["--no-strict"], [1, False, "default", "COMMANDLINE"]),
        ([expected_flag, "2", "--explicit-alias", "set"], [2, None, "set", "DEFAULT"]),
    ]:
        result = runner.invoke(app, ["fixture", *flags])
        assert result.exit_code == 0 and not result.stderr, result.output
        assert json.loads(result.stdout) == expected, result.output
    invalid_flag = "--item-count" if expected_flag == "--ITEM-COUNT" else "--ITEM-COUNT"
    invalid = runner.invoke(app, ["fixture", invalid_flag, "2"])
    assert (invalid.exit_code, invalid.stdout) == (2, ""), invalid.output
    assert "No such option" in invalid.stderr, invalid.output
    help_result = runner.invoke(app, ["fixture", "--help"])
    assert help_result.exit_code == 0, help_result.output
    assert expected_flag in help_result.stdout and "ITEM-COUNT" in help_result.stdout
    completion = runner.invoke(
        app,
        [],
        prog_name="fixture",
        env={
            "_FIXTURE_COMPLETE": "complete_bash",
            "COMP_WORDS": "fixture discover --profile special --item a",
            "COMP_CWORD": "5",
        },
    )
    assert (completion.exit_code, completion.stdout) == (0, "alpha\n"), completion.output
    assert json.loads(completion.stderr) == [[], {"profile": "special", "item": ""}, "a"], (
        completion.output
    )
    check_callbacks(runner)
    check_passthrough(runner)
    print(f"fixture passed: {expected_flag}, aliases, tri-state, provenance, completion, callbacks")


def check_passthrough(runner: CliRunner) -> None:
    forwarding = typer.Typer()

    @forwarding.command(context_settings={"allow_extra_args": True})
    def invoke(ctx: typer.Context) -> None:
        typer.echo(json.dumps(ctx.args))

    before = runner.invoke(forwarding, ["unexpected"])
    after = runner.invoke(forwarding, ["--", "unexpected"])
    assert (
        (before.exit_code, before.stdout)
        == (after.exit_code, after.stdout)
        == (
            0,
            '["unexpected"]\n',
        )
    )
    unknown = runner.invoke(forwarding, ["--unrecognized"])
    assert unknown.exit_code == 2 and not unknown.stdout, unknown.output


def check_recipe() -> None:
    recipe = (
        "[positional-arguments]\n"
        "capture *args:\n"
        "    @python3 -c 'import sys, json; print(json.dumps(sys.argv[1:]))' \"$@\"\n"
    )
    arguments = ["two words", "$HOME", "; literal", "--marker"]
    result = subprocess.run(
        ["just", "--justfile", "-", "--working-directory", str(Path.cwd()), "capture", *arguments],
        input=recipe,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == arguments, result
    print("recipe fixture passed: positional arguments, quoting, option-looking values")


def check_rich_text() -> None:
    target = StringIO()
    console = Console(file=target, force_terminal=False, color_system=None)
    external = "[red]message[/red] \x1b[31m \x1b]8;;https://example.invalid\x1b\\"
    console.print(Text(external))
    console.print(external, markup=False, highlight=False)
    assert target.getvalue() == (external + "\n") * 2
    print("Rich fixture passed: literal rendering retains raw terminal controls")


def check_installed() -> None:
    ci = Path(sys.executable).with_name("ci")
    typer_cli = ci.with_name("typer")
    env = {**os.environ, "CORPUS_DATABASE__URL": "invalid", "COLUMNS": "100", "NO_COLOR": "1"}
    for cmd, code, stdout_marker, stderr_marker in [
        ([ci, "--help"], 0, "Commands", ""),
        ([ci, "schema", "native-candidate", "--help"], 0, "--out", ""),
        ([ci, "schema", "diff", "--json", "--unknown-flag"], 2, "", "No such option"),
        (
            [
                typer_cli,
                "--app",
                "app",
                "corpus_structure.cli.app",
                "utils",
                "docs",
                "--name",
                "ci",
            ],
            0,
            "# `ci`",
            "",
        ),
    ]:
        result = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=25, check=False
        )
        assert result.returncode == code, (cmd, result)
        assert stdout_marker in result.stdout if stdout_marker else not result.stdout, result
        assert stderr_marker in result.stderr if stderr_marker else not result.stderr, result
        print(f"installed probe passed: {' '.join([cmd[0].name, *cmd[1:]])}")


def compare() -> None:
    subprocess.run([sys.executable, __file__], check=True)
    with TemporaryDirectory(prefix="cli-typer-028-") as overlay:
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                sys.executable,
                "--no-deps",
                "--target",
                overlay,
                "typer==0.28.0",
            ],
            check=True,
        )
        subprocess.run(
            [sys.executable, __file__],
            env={**os.environ, "PYTHONPATH": overlay},
            check=True,
        )
    check_recipe()
    check_rich_text()


if __name__ == "__main__":
    if sys.argv[1:] == ["--compare"]:
        compare()
        raise SystemExit(0)
    assert platform.python_version() == "3.14.10"
    assert version("rich") == "15.0.0"
    assert typer.__version__ in {"0.27.3", "0.28.0"}
    print(f"Python {platform.python_version()}, Typer {typer.__version__}, Rich {version('rich')}")
    check_fixture()
    check_installed()
