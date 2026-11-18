"""The output and exit contract, exercised through a probe command registered the way a later
command module registers itself (`register(group)`)."""

import hashlib
import json
import shlex
from typing import Annotated, ClassVar, Literal

import pytest
import typer
from typer.testing import CliRunner

from corpus_tooling.envelope import (
    Baseline,
    Column,
    Item,
    SkippedInput,
    TargetPython,
    ToolInfo,
    Unresolved,
    build_envelope,
)
from corpus_tooling.library.app import REGISTRATIONS, make_library_app
from corpus_tooling.library.context import library_envelope, library_state
from corpus_tooling.output import (
    DEFAULT_LIMIT,
    JsonOpt,
    LimitOpt,
    OffsetOpt,
    StrictOpt,
    ToolFailure,
    diagnostic,
    emit,
    next_page_command,
    write_stdout,
)

BOX_DRAWING = set(chr(code) for code in range(0x2500, 0x2580))


class ProbeSite(Item):
    kind: Literal["probe_site"] = "probe_site"
    path: str
    line: int
    note: str = ""

    columns: ClassVar = (Column("path"), Column("line"), Column("note"))
    sort_fields: ClassVar = ("path", "line")


class ProbeUnresolved(Unresolved):
    kind: Literal["assignment_alias", "instance_member"]
    expression: str


def probe(
    ctx: typer.Context,
    names: Annotated[list[str] | None, typer.Argument()] = None,
    json: JsonOpt = False,
    limit: LimitOpt = DEFAULT_LIMIT,
    offset: OffsetOpt = 0,
    strict: StrictOpt = False,
    unresolved: Annotated[bool, typer.Option("--unresolved")] = False,
    skipped: Annotated[bool, typer.Option("--skipped")] = False,
    fail: Annotated[bool, typer.Option("--fail")] = False,
    fail_late: Annotated[bool, typer.Option("--fail-late")] = False,
    crash: Annotated[bool, typer.Option("--crash")] = False,
    read_installation: Annotated[bool, typer.Option("--read-installation")] = False,
    emit_twice: Annotated[bool, typer.Option("--emit-twice")] = False,
    fail_after_emit: Annotated[bool, typer.Option("--fail-after-emit")] = False,
) -> None:
    diagnostic("probe: scanning \x1b[31mfive\x1b[0m sites")
    if fail:
        raise ToolFailure("probe_failed", "the probe could not run", "Pass fewer flags.")
    if crash:
        raise ValueError("unexpected")
    state = library_state(ctx)
    target = state.target
    if fail_late:
        raise ToolFailure("probe_failed", "the probe failed after resolving", "Pass less.")
    if read_installation:
        assert state.installation.distributions
    sites = [ProbeSite(path=f"pkg/m{n}.py", line=n) for n in (3, 1, 5, 2, 4)]
    sites.append(ProbeSite(path="pkg/z.py", line=9, note="\x1b]0;title\x07evil\ttab"))
    envelope = library_envelope(
        ctx,
        ProbeSite,
        sites,
        limit=limit,
        offset=offset,
        authorities={"probe": "1.0"},
        scanned=6,
        # No unresolved_type: it is inferred from the rows.
        unresolved=[
            ProbeUnresolved(
                kind="instance_member",
                subject="m.dump",
                location="pkg/m1.py:4:1",
                expression="m.dump()",
            )
        ]
        if unresolved
        else [],
        skipped_inputs=[SkippedInput(input="pkg/bad.py", reason="parse_error")] if skipped else [],
        notes=[f"target python {target.environment.python_version}"],
    )
    emit(envelope, json=json, strict=strict)
    if emit_twice:
        emit(envelope, json=json, strict=strict)
    if fail_after_emit:
        raise ToolFailure("probe_failed", "late failure", "Nothing.")


def selection_probe(ctx: typer.Context, json: JsonOpt = False) -> None:
    """Stands in for a selection-class command: it needs the project."""
    library_state(ctx).target.require_project()
    emit(library_envelope(ctx, ProbeSite, [], limit=0, offset=0), json=json)


def register(group: typer.Typer) -> None:
    group.command("probe")(probe)
    group.command("selection-probe")(selection_probe)


@pytest.fixture
def cli() -> typer.Typer:
    root = typer.Typer()

    @root.callback()
    def _root() -> None: ...

    root.add_typer(make_library_app((*REGISTRATIONS, register)), name="library")
    return root


def _run(cli: typer.Typer, *args: str):
    return CliRunner().invoke(cli, ["library", *args])


def test_json_stdout_is_exactly_one_envelope_and_diagnostics_go_to_stderr(cli, trees) -> None:
    result = _run(cli, "--project", str(trees.project), "probe", "--json")
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)  # one document, nothing else on stdout
    assert result.stdout.count("\n") == 1
    assert "probe: scanning five sites" in result.stderr
    assert "\x1b" not in result.stderr
    assert envelope["schema"] == "tooling.library/1"
    assert envelope["status"] == "ok"
    assert "error" not in envelope
    assert envelope["view"] == "probe_site"
    assert [(item["path"], item["line"]) for item in envelope["items"]] == [
        ("pkg/m1.py", 1),
        ("pkg/m2.py", 2),
        ("pkg/m3.py", 3),
        ("pkg/m4.py", 4),
        ("pkg/m5.py", 5),
        ("pkg/z.py", 9),
    ]
    assert envelope["tool"]["authorities"] == {"probe": "1.0"}
    assert envelope["command"] == f"tooling library --project {trees.project} probe --json"
    assert envelope["coverage"] == {
        "scanned": 6,
        "no_hit_scopes": [],
        "excluded": [],
        "skipped_inputs": [],
        "unresolved": [],
        "unavailable_metadata": [],
    }
    assert envelope["truncated"] == []
    assert envelope["notes"] == ["target python 3.12.7"]


def test_fixture_target_reports_its_python_and_lock_not_the_tools(cli, trees) -> None:
    result = _run(cli, "--project", str(trees.project), "probe", "--json")
    baseline = json.loads(result.stdout)["baseline"]
    lock_digest = hashlib.sha256((trees.project / "uv.lock").read_bytes()).hexdigest()
    assert baseline["python"] == {
        "version": "3.12.7",
        "implementation": "CPython",
        "environment": ".venv",
    }
    assert baseline["lock_digest"] == f"sha256:{lock_digest}"
    assert baseline["project"] == "."
    assert baseline["revision"] is None
    assert baseline["dirty_paths"] == []


def test_default_project_is_the_nearest_ancestor_with_a_lock(cli, trees, monkeypatch) -> None:
    monkeypatch.chdir(trees.project / "packages" / "one")
    result = _run(cli, "probe", "--json")
    assert result.exit_code == 0, result.output
    baseline = json.loads(result.stdout)["baseline"]
    assert baseline["python"]["version"] == "3.12.7"
    assert baseline["lock_digest"] is not None


def test_unresolved_rows_exit_zero_and_skipped_inputs_fail_only_under_strict(cli, trees) -> None:
    project = ("--project", str(trees.project))
    result = _run(cli, *project, "probe", "--json", "--unresolved")
    assert result.exit_code == 0
    assert json.loads(result.stdout)["coverage"]["unresolved"] == [
        {
            "kind": "instance_member",
            "subject": "m.dump",
            "location": "pkg/m1.py:4:1",
            "detail": "",
            "expression": "m.dump()",
        }
    ]
    assert _run(cli, *project, "probe", "--json", "--skipped").exit_code == 0
    strict = _run(cli, *project, "probe", "--json", "--skipped", "--strict")
    assert strict.exit_code == 1
    assert json.loads(strict.stdout)["coverage"]["skipped_inputs"] == [
        {"input": "pkg/bad.py", "reason": "parse_error", "detail": ""}
    ]
    assert _run(cli, *project, "probe", "--json", "--unresolved", "--strict").exit_code == 0


def test_piped_output_is_plain_and_ends_with_the_truncation_line(cli, trees) -> None:
    result = _run(cli, "--project", str(trees.project), "probe", "--limit", "2", "--offset", "1")
    assert result.exit_code == 0, result.output
    assert not BOX_DRAWING & set(result.stdout)
    assert "\x1b" not in result.stdout
    lines = result.stdout.splitlines()
    assert lines[1] == "# columns\tpath\tline\tnote"
    assert lines[2:4] == ["pkg/m2.py\t2\t-", "pkg/m3.py\t3\t-"]
    assert lines[-1] == (
        "# truncated items: shown 2 of 6; next: "
        f"tooling library --project {trees.project} probe --limit 2 --offset 3"
    )


def test_plain_cells_are_literal_single_line_text(cli, trees) -> None:
    result = _run(cli, "--project", str(trees.project), "probe", "--offset", "5")
    assert "pkg/z.py\t9\tevil tab" in result.stdout.splitlines()


def test_terminal_output_is_a_rich_table(cli, trees) -> None:
    result = CliRunner().invoke(
        cli,
        ["library", "--project", str(trees.project), "probe", "--limit", "2"],
        env={"TTY_COMPATIBLE": "1", "COLUMNS": "200", "NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.output
    assert "probe_site (2)" in result.stdout
    assert "# columns" not in result.stdout
    assert "truncated items: shown 2 of 6; next:" in result.stdout


def test_tool_failure_is_exit_3_with_the_failed_envelope(cli, trees) -> None:
    result = _run(cli, "--project", str(trees.project), "probe", "--json", "--fail")
    assert result.exit_code == 3
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "failed"
    assert envelope["error"] == {
        "kind": "probe_failed",
        "message": "the probe could not run",
        "remedy": "Pass fewer flags.",
    }
    assert envelope["items"] == []
    assert envelope["coverage"]["skipped_inputs"] == []
    rendered = _run(cli, "--project", str(trees.project), "probe", "--fail")
    assert rendered.exit_code == 3
    assert rendered.stdout == ""
    assert "the probe could not run [probe_failed]" in rendered.stderr


def test_unexpected_error_is_an_internal_failure_envelope(cli, trees) -> None:
    result = _run(cli, "--project", str(trees.project), "probe", "--json", "--crash")
    assert result.exit_code == 3
    assert json.loads(result.stdout)["error"]["kind"] == "internal_error"
    assert "ValueError: unexpected" in result.stderr


def test_missing_environment_is_a_target_failure(cli, trees) -> None:
    result = _run(cli, "--project", str(trees.root / "workspace" / "tool"), "probe", "--json")
    assert result.exit_code == 3
    error = json.loads(result.stdout)["error"]
    assert error["kind"] == "environment_not_found"
    assert "--python" in error["remedy"]


def test_usage_error_is_exit_2_without_an_envelope(cli, trees) -> None:
    result = _run(cli, "--project", str(trees.project), "probe", "--limit", "-1")
    assert result.exit_code == 2
    assert result.stdout == ""


def test_environment_of_another_project_carries_the_mismatch_note(cli, trees) -> None:
    result = _run(
        cli, "--project", str(trees.project), "--python", str(trees.elsewhere), "probe", "--json"
    )
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    (note, *_) = envelope["notes"]
    assert note.startswith(f"environment {trees.elsewhere.as_posix()} is not the project's own")
    assert envelope["baseline"]["project"] == "."
    assert envelope["baseline"]["python"]["environment"] == trees.elsewhere.as_posix()


def test_interpreter_path_names_its_environment(cli, trees) -> None:
    interpreter = trees.project / ".venv" / "bin" / "python"
    interpreter.parent.mkdir()
    interpreter.write_text("")
    result = _run(
        cli, "--project", str(trees.project), "--python", str(interpreter), "probe", "--json"
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["notes"] == ["target python 3.12.7"]


def test_environment_without_project_is_refused_by_selection_accepted_by_baseline(
    cli, trees
) -> None:
    selection = _run(cli, "--project", str(trees.env_only), "selection-probe", "--json")
    assert selection.exit_code == 3
    assert json.loads(selection.stdout)["error"]["kind"] == "no_project"
    baseline = _run(cli, "--project", str(trees.env_only), "baseline", "--json")
    assert baseline.exit_code == 0, baseline.output
    envelope = json.loads(baseline.stdout)
    assert envelope["baseline"]["project"] is None
    assert envelope["baseline"]["lock_digest"] is None
    assert envelope["items"] == []
    assert envelope["notes"] == [
        f"{(trees.env_only / '.venv').as_posix()} has no uv project; installation facts only, "
        "selection-class commands refuse this target"
    ]


def test_a_closed_stdout_ends_quietly_with_an_exit_code(monkeypatch, capsys) -> None:
    class Closed:
        def write(self, _: str) -> int:
            raise BrokenPipeError

        def flush(self) -> None: ...

    monkeypatch.setattr("sys.stdout", Closed())
    with pytest.raises(typer.Exit) as stopped:
        write_stdout("{}\n")
    assert stopped.value.exit_code == 74
    assert "stdout closed" in capsys.readouterr().err


def test_next_page_keeps_options_before_the_argument_separator() -> None:
    assert next_page_command("tooling library census --json --offset 2 -- -x", 7) == (
        "tooling library census --offset 7 -- -x"
    )


def test_failure_after_resolution_keeps_the_baseline_and_target_notes(cli, trees) -> None:
    result = _run(
        cli,
        "--project",
        str(trees.project),
        "--python",
        str(trees.elsewhere),
        "probe",
        "--json",
        "--fail-late",
    )
    assert result.exit_code == 3
    envelope = json.loads(result.stdout)
    assert envelope["status"] == "failed"
    assert envelope["baseline"]["python"]["version"] == "3.12.7"
    assert envelope["baseline"]["project"] == "."
    (note,) = envelope["notes"]
    assert note.startswith(f"environment {trees.elsewhere.as_posix()} is not the project's own")


def test_unreadable_installation_metadata_reaches_coverage_and_strict(cli, trees) -> None:
    project = ("--project", str(trees.project))
    result = _run(cli, *project, "probe", "--json", "--read-installation")
    assert result.exit_code == 0, result.output
    skipped = json.loads(result.stdout)["coverage"]["skipped_inputs"]
    assert [(row["input"].rsplit("/", 1)[-1], row["reason"]) for row in skipped] == [
        ("broken-0.0.0.dist-info", "unreadable_metadata"),
        ("delta-1.0.0.dist-info", "unreadable_metadata"),
    ]
    assert _run(cli, *project, "probe", "--json", "--read-installation", "--strict").exit_code == 1
    # A command that never reads the installation reports none of it.
    assert _run(cli, *project, "probe", "--json", "--strict").exit_code == 0


def test_a_second_emit_or_a_late_failure_never_adds_a_second_result(cli, trees) -> None:
    for flag, message in (
        ("--emit-twice", "emit called twice"),
        ("--fail-after-emit", "late failure"),
    ):
        result = _run(cli, "--project", str(trees.project), "probe", "--json", flag)
        assert result.exit_code == 3
        assert json.loads(result.stdout)["status"] == "ok"  # exactly one document
        assert "failed after the result was delivered" in result.stderr
        assert message in result.stderr


def test_terminal_rendering_strips_control_sequences(cli, trees) -> None:
    result = CliRunner().invoke(
        cli,
        ["library", "--project", str(trees.project), "probe", "--offset", "5"],
        env={"TTY_COMPATIBLE": "1", "COLUMNS": "200", "NO_COLOR": "1"},
    )
    assert result.exit_code == 0, result.output
    assert "evil tab" in result.stdout
    assert "\x1b]" not in result.stdout
    assert "\x07" not in result.stdout
    assert "title" not in result.stdout


def test_next_page_command_with_positional_arguments_continues_the_list(cli, trees) -> None:
    first = _run(cli, "--project", str(trees.project), "probe", "alpha", "beta", "--limit", "4")
    last = first.stdout.splitlines()[-1]
    prefix = "# truncated items: shown 4 of 6; next: "
    assert last == (
        f"{prefix}tooling library --project {trees.project} probe --limit 4 alpha beta --offset 4"
    )
    following = shlex.split(last.removeprefix(prefix))[1:]  # drop the program name
    second = CliRunner().invoke(cli, following)
    assert second.exit_code == 0, second.output
    rows = [line for line in second.stdout.splitlines() if not line.startswith("#")]
    assert rows == ["pkg/m5.py\t5\t-", "pkg/z.py\t9\tevil tab"]


def _envelope_inputs() -> dict:
    return {
        "tool": ToolInfo(version="0"),
        "command": "tooling library probe",
        "baseline": Baseline(
            revision=None,
            dirty_paths=[],
            project=None,
            python=TargetPython(version="3.12.7", environment="/env"),
            platform="linux-x86_64",
            lock_digest=None,
        ),
        "limit": 0,
        "offset": 0,
    }


class OtherUnresolved(Unresolved):
    kind: Literal["other"]


def test_rows_must_match_their_declared_types() -> None:
    row = ProbeUnresolved(kind="assignment_alias", subject="s", location="l", expression="e")
    other = OtherUnresolved(kind="other", subject="s", location="l")
    with pytest.raises(TypeError, match="mix types"):
        build_envelope(ProbeSite, [], unresolved=[row, other], **_envelope_inputs())
    with pytest.raises(TypeError, match="exactly Unresolved"):
        build_envelope(
            ProbeSite, [], unresolved_type=Unresolved, unresolved=[row], **_envelope_inputs()
        )
    inferred = build_envelope(ProbeSite, [], unresolved=[row], **_envelope_inputs())
    assert json.loads(inferred.model_dump_json())["coverage"]["unresolved"][0]["expression"] == "e"


def test_workspace_member_selects_the_workspace_lock_and_environment(cli, trees) -> None:
    result = _run(cli, "--project", str(trees.project / "packages" / "one"), "probe", "--json")
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.stdout)
    lock = hashlib.sha256((trees.project / "uv.lock").read_bytes()).hexdigest()
    assert envelope["baseline"]["project"] == "."
    assert envelope["baseline"]["lock_digest"] == f"sha256:{lock}"
    assert envelope["baseline"]["python"]["environment"] == ".venv"
    assert envelope["notes"] == [
        "workspace member packages/one of the workspace at .; its lock and environment are "
        "the workspace's",
        "target python 3.12.7",
    ]
    selection = _run(
        cli, "--project", str(trees.project / "packages" / "one"), "selection-probe", "--json"
    )
    assert selection.exit_code == 0, selection.output


def test_working_directory_inside_a_member_records_the_member(cli, trees, monkeypatch) -> None:
    monkeypatch.chdir(trees.project / "packages" / "two")
    result = _run(cli, "probe", "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["notes"][0].startswith("workspace member packages/two ")


def test_unlocked_project_is_refused_by_selection_commands(cli, trees) -> None:
    # Excluded from the workspace and without its own uv.lock: a project, but not a locked one.
    excluded = trees.project / "packages" / "excluded"
    result = _run(
        cli,
        "--project",
        str(excluded),
        "--python",
        str(trees.project / ".venv"),
        "selection-probe",
        "--json",
    )
    assert result.exit_code == 3
    assert json.loads(result.stdout)["error"]["kind"] == "no_lock"


def test_system_site_packages_are_noted_as_not_read(cli, trees) -> None:
    config = trees.elsewhere / "pyvenv.cfg"
    config.write_text(
        config.read_text().replace(
            "include-system-site-packages = false", "include-system-site-packages = true"
        )
    )
    result = _run(
        cli, "--python", str(trees.elsewhere), "--project", str(trees.project), "probe", "--json"
    )
    assert result.exit_code == 0, result.output
    assert (
        f"{trees.elsewhere.as_posix()} sets include-system-site-packages = true; the base "
        "interpreter's packages are not read"
    ) in json.loads(result.stdout)["notes"]
