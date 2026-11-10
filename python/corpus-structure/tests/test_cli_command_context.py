"""Native authoring examples, scalar boundaries and same-snapshot selection."""

import json

import pytest

from corpus_structure.settings import Settings


def refuse():
    pytest.fail("invalid grammar acquired settings")


@pytest.mark.parametrize("command", ["compile", "check", "inspect"])
@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--max-errors", "0"),
        ("--max-errors", "1001"),
        ("--max-depth", "17"),
        ("--max-depth", "bad"),
        ("--max-bytes", "1023"),
        ("--max-bytes", "1048577"),
    ],
)
def test_correction_scalars_refuse_before_acquisition(cli, command, option, value):
    args = ["schema", command]
    if command == "inspect":
        args += ["--release", "release", "--subject-kind", "operation", "--subject", "op"]
    result = cli(*args, option, value, settings=refuse)
    assert result.exit_code == 2, result.output


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("--dependency-after", "-1"),
        ("--dependency-limit", "0"),
        ("--dependency-limit", "1001"),
        ("--domain", "../escape"),
    ],
)
def test_candidate_scalar_grammar(cli, option, value):
    result = cli("schema", "check", option, value, settings=refuse)
    assert result.exit_code == 2, result.output


@pytest.mark.parametrize(
    ("args", "profile", "source", "section"),
    [
        ([], "development", "default", "database"),
        (["--target", "development"], "development", "commandline", "database"),
        (["--target", "deployment"], "deployment", "commandline", "deployment"),
    ],
)
def test_context_selection_is_the_original_snapshot(cli, tmp_path, args, profile, source, section):
    calls = []

    def factory():
        calls.append(True)
        return Settings(
            database={"url": "postgresql://dev:private@localhost/development"},
            deployment={"url": "postgresql://prod:secret@localhost/production"},
        )

    result = cli(
        "context",
        "show",
        *args,
        "--json",
        settings=factory,
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    selection = report["selection"]
    assert calls == [True]
    assert selection["profile"] == profile
    assert selection["target_parameter_source"] == source
    assert selection["settings_section"] == section
    assert selection["standing"] == "configured_unobserved"
    assert selection["observed_binding"] is report["observed_binding"] is None
    key = section + ".url"
    assert selection["resources"][key] == report["settings"]["resolved"][key]
    assert selection["origins"][key] == "constructor"
    assert "private" not in result.stdout and "secret" not in result.stdout


def test_context_unavailable_deployment_and_sequential_snapshot(cli, tmp_path):
    env = {"CORPUS_CI_RESULTS": str(tmp_path)}
    missing = cli(
        "context",
        "show",
        "--target",
        "deployment",
        "--json",
        settings=lambda: Settings(deployment=None),
        env=env,
    )
    assert missing.exit_code == 1, missing.output
    second = cli("context", "show", "--json", settings=lambda: Settings(deployment=None), env=env)
    assert second.exit_code == 0, second.output
    assert json.loads(second.stdout)["selection"]["profile"] == "development"


def test_repeated_pack_names_and_check_custody(cli, monkeypatch, tmp_path):
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.semantic import regeneration
    from corpus_structure.semantic.refusals import SemanticRefusal

    selected = []

    def prepare(paths):
        selected.extend(paths)
        raise SemanticRefusal("controlled missing pack")

    monkeypatch.setattr(regeneration, "acquire_packs", prepare)
    result = cli(
        "schema",
        "check",
        "--domain",
        "first",
        "--domain",
        "second",
        "--retain-diagnostics",
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert result.exit_code == 1, result.output
    assert [str(path) for path in selected] == ["domains/first", "domains/second"]
    (retained,) = ResultStore(tmp_path).list(None, 20, None).results
    assert retained.action == "schema.check" and retained.outcome == "failed"


@pytest.mark.parametrize(
    ("args", "raw", "bound"),
    [
        ([], False, 8388608),
        (["--raw-evidence", "--no-raw-evidence"], False, 8388608),
        (["--max-bytes", "1024"], False, 1024),
        (["--raw-evidence", "--max-bytes", "1048577"], True, 1048577),
    ],
)
def test_retained_diagnostic_has_its_own_native_byte_bound(
    cli, monkeypatch, tmp_path, args, raw, bound
):
    from corpus_structure.cli import diagnostic_artifacts
    from corpus_structure.cli.managed import ResultStore

    with ResultStore(tmp_path).operation("diagnostic-bound") as invocation:
        pass
    calls = []

    def read(store, result_id, **options):
        calls.append((result_id, options))
        return {"retained": True}

    monkeypatch.setattr(diagnostic_artifacts, "read_diagnostic", read)
    result = cli(
        "schema",
        "diagnostic",
        invocation.id,
        *args,
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert result.exit_code == 0, result.output
    assert calls == [(invocation.id, {"raw_evidence": raw, "max_bytes": bound})]


def test_native_reference_never_calls_callbacks_and_whole_tree_is_complete():
    import typer

    from corpus_structure.cli.reference import command_markdown

    app = typer.Typer()
    group = typer.Typer()
    app.callback()(refuse)
    group.callback()(refuse)
    group.command("leaf")(refuse)
    app.add_typer(group, name="subtree")
    app.command("sibling")(refuse)
    reference = command_markdown(app)
    assert all(
        name in reference for name in ("`ci`", "`ci subtree`", "`ci subtree leaf`", "`ci sibling`")
    )


@pytest.mark.parametrize(
    ("command", "meanings"),
    [
        (
            "inspect",
            (
                "patch hunks or SQL change entries; default 8",
                "Continue after this hunk ordinal",
                "Continue SQL detail after this ordinal",
            ),
        ),
        (
            "inspect-candidate",
            (
                "operations or SQL after this ordinal; not a contract cursor",
                "operation, SQL change or contract detail entries",
                "Required contract subject kind",
                "Required exact contract subject identifier",
                "Optional contract property selector",
                "Opaque contract-detail continuation returned by the same bound request",
                "distinct from --after",
            ),
        ),
    ],
)
def test_model_inspection_reference_explains_page_units_and_continuations(cli, command, meanings):
    reference = cli("docs", "commands", "model", "change", command, "--stdout", settings=refuse)
    assert reference.exit_code == 0, reference.output
    for meaning in meanings:
        assert meaning in reference.stdout


def test_selected_origins_are_preserved_without_relabelling():
    import typer

    from corpus_structure.cli.app import app
    from corpus_structure.cli.target import configured_selection
    from corpus_structure.settings import SettingsReport

    ctx = typer.Context(typer.main.get_command(app))
    report = SettingsReport(
        resolved={
            "database.url": "masked",
            "database.reader_url": "reader",
            "database.template": "template",
            "database.pool_min_size": "1",
            "deployment.url": "other",
        },
        unknown_env=(),
        origins={
            "database.url": "mixed",
            "database.reader_url": "derived",
            "database.template": "default",
        },
    )
    selection = configured_selection(ctx, Settings(), "development", report=report)
    assert selection.origins == {
        "database.url": "mixed",
        "database.reader_url": "derived",
        "database.template": "default",
        "database.pool_min_size": "unknown",
    }
    assert "deployment.url" not in selection.resources


def test_successful_check_owns_its_retained_operation(cli, tmp_path):
    from corpus_structure.cli.managed import ResultStore

    result = cli(
        "schema",
        "check",
        "--retain-diagnostics",
        "--json",
        env={"CORPUS_CI_RESULTS": str(tmp_path)},
    )
    assert result.exit_code == 0, result.output
    (manifest,) = ResultStore(tmp_path).list(None, 20, None).results
    assert manifest.action == "schema.check" and manifest.outcome == "passed"
